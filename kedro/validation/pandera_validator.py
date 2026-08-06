"""Pandera adapter for catalog-native dataset validation.

All pandera imports live inside functions so that pandera remains an optional
dependency of Kedro.

Detection targets pandera's per-backend namespaces:
`pandera.api.dataframe.model.DataFrameModel` is the shared base of the
`pandera.pandas`/`pandera.polars`/`pandera.pyspark` `DataFrameModel`
classes, and the per-backend `DataFrameSchema` container classes are
accepted as instances. The deprecated top-level `pandera.DataFrameModel`
is deliberately not referenced.
"""

from __future__ import annotations

import inspect
import logging
import math
from typing import Any, cast

from kedro.validation.core import (
    _MAX_FAILURE_EXAMPLES,
    CheckFailure,
    DataValidationError,
    ValidationConfigurationError,
)

logger = logging.getLogger(__name__)

#: Sentinel separating "pandera reported no errors" from "there is no pandera
#: report to read".
_NO_REPORT = object()


def _is_pandera_model(cls: Any) -> bool:
    """Check whether `cls` is a pandera `DataFrameModel` subclass.

    Uses the shared base class so pandas, polars and pyspark models are all
    detected. Returns `False` if pandera is not installed.
    """
    try:
        from pandera.api.dataframe.model import DataFrameModel as _BaseModel
    except ImportError:
        return False
    return inspect.isclass(cls) and issubclass(cls, _BaseModel)


def _is_pandera_schema_instance(obj: Any) -> bool:
    """Check whether `obj` is a pandera `DataFrameSchema` instance.

    Each backend's container class import is guarded individually as polars
    and pyspark are optional extras of pandera. Returns `False` if pandera
    is not installed.
    """
    container_classes: list[type] = []
    try:
        from pandera.api.pandas.container import DataFrameSchema as _PandasSchema

        container_classes.append(_PandasSchema)
    except ImportError:
        # The pandas backend of pandera is not installed; skip its
        # container class.
        pass
    try:
        from pandera.api.polars.container import DataFrameSchema as _PolarsSchema

        container_classes.append(_PolarsSchema)
    except ImportError:
        # The polars backend of pandera is not installed; skip its
        # container class.
        pass
    try:
        from pandera.api.pyspark.container import DataFrameSchema as _PySparkSchema

        container_classes.append(_PySparkSchema)
    except ImportError:
        # The pyspark backend of pandera is not installed; skip its
        # container class.
        pass
    if not container_classes:
        return False
    return isinstance(obj, tuple(container_classes))


def pandera_adapter(obj: Any, options: dict) -> PanderaValidator | None:
    """Adapt a pandera schema object into a `PanderaValidator`.

    Args:
        obj: The imported object from a validator `class_path`.
        options: Options from the validator spec, forwarded to
            `PanderaValidator`.

    Returns:
        A `PanderaValidator` when `obj` is a pandera `DataFrameModel`
        subclass or `DataFrameSchema` instance, otherwise `None`
        (including when pandera is not installed).

    Raises:
        ValidationConfigurationError: If `options` contains keys not
            supported by `PanderaValidator`.
    """
    if not (_is_pandera_model(obj) or _is_pandera_schema_instance(obj)):
        return None
    try:
        return PanderaValidator(obj, **options)
    except TypeError as exc:
        name = getattr(obj, "__name__", type(obj).__name__)
        raise ValidationConfigurationError(
            f"Unsupported option(s) for pandera validator '{name}': {exc}. "
            f"Supported options: lazy, head, tail, sample, random_state."
        ) from exc


def _failure_cases_records(failure_cases: Any) -> list[dict]:
    """Normalise a backend failure-cases frame into a list of dicts.

    Only pandas and polars reach this helper: they report failures by raising,
    and the raised error carries a frame of failure cases. Pyspark never
    raises, so its failures are read from the accessor on the returned
    DataFrame instead (see `PanderaValidator._validate_pyspark`).
    """
    if failure_cases is None:
        return []
    # pandas DataFrame
    to_dict = getattr(failure_cases, "to_dict", None)
    if to_dict is not None and hasattr(failure_cases, "columns"):
        try:
            return cast("list[dict]", to_dict(orient="records"))
        except TypeError:
            pass
    # polars DataFrame
    to_dicts = getattr(failure_cases, "to_dicts", None)
    if to_dicts is not None:
        return cast("list[dict]", to_dicts())
    if isinstance(failure_cases, list):
        return [
            record if isinstance(record, dict) else {"failure_case": record}
            for record in failure_cases
        ]
    return []


def _clean_cell(value: Any) -> str | None:
    """Normalise a failure-case cell value (may be None or NaN)."""
    if value is None:
        return None
    try:
        is_nan = math.isnan(value)
    except TypeError:
        is_nan = False
    if is_nan:
        return None
    return str(value)


def _failures_from_schema_errors(exc: Exception) -> list[CheckFailure]:
    """Build grouped `CheckFailure` objects from a pandera `SchemaErrors`.

    Failure cases are grouped by `(column, check)`; each group records its
    total failure count and up to `_MAX_FAILURE_EXAMPLES` example values.
    """
    records = _failure_cases_records(getattr(exc, "failure_cases", None))
    if not records:
        return [CheckFailure(message=str(exc))]

    grouped: dict[tuple, dict[str, Any]] = {}
    for record in records:
        column = _clean_cell(record.get("column"))
        check = _clean_cell(record.get("check"))
        group = grouped.setdefault(
            (column, check), {"count": 0, "examples": [], "index": None}
        )
        group["count"] += 1
        if len(group["examples"]) < _MAX_FAILURE_EXAMPLES:
            group["examples"].append(record.get("failure_case"))
        if group["index"] is None:
            group["index"] = record.get("index")

    failures = []
    for (column, check), group in grouped.items():
        target = f"column '{column}'" if column else "dataframe"
        # Not every pandera failure names a check: schema-level failures such
        # as a mismatched index report none.
        message = (
            f"Check '{check}' failed for {target}"
            if check is not None
            else f"Schema validation failed for {target}"
        )
        failures.append(
            CheckFailure(
                message=message,
                check=check,
                column=column,
                failure_count=group["count"],
                failure_examples=group["examples"],
                index=group["index"],
            )
        )
    return failures


def _failure_from_schema_error(exc: Exception) -> CheckFailure:
    """Build a single `CheckFailure` from a non-lazy pandera `SchemaError`."""
    records = _failure_cases_records(getattr(exc, "failure_cases", None))
    column = _clean_cell(getattr(getattr(exc, "schema", None), "name", None))
    return CheckFailure(
        message=str(exc),
        check=_clean_cell(getattr(exc, "check", None)),
        column=column,
        failure_count=max(len(records), 1),
        failure_examples=[
            record.get("failure_case") for record in records[:_MAX_FAILURE_EXAMPLES]
        ],
        index=records[0].get("index") if records else None,
    )


class PanderaValidator:
    """Validates data against a pandera schema (model class or schema instance).

    Supports pandas and polars frames via `schema.validate` and pyspark
    DataFrames via pandera's accessor-based error reporting (pandera's pyspark
    backend never raises).
    """

    def __init__(  # noqa: PLR0913
        self,
        schema: Any,
        lazy: bool = True,
        head: int | None = None,
        tail: int | None = None,
        sample: int | None = None,
        random_state: int | None = None,
    ) -> None:
        """Initialise the validator.

        Args:
            schema: A pandera `DataFrameModel` subclass or
                `DataFrameSchema` instance.
            lazy: Collect all failures before raising (default `True`).
            head: Validate only the first `head` rows.
            tail: Validate only the last `tail` rows.
            sample: Validate a random sample of `sample` rows.
            random_state: Seed for `sample`.
        """
        self._schema = schema
        self._lazy = lazy
        self._head = head
        self._tail = tail
        self._sample = sample
        self._random_state = random_state
        self._lazyframe_warned = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._validator_path()})"

    def _validator_path(self) -> str:
        """Dotted path of the schema class for error reporting."""
        target = self._schema if inspect.isclass(self._schema) else type(self._schema)
        return f"{target.__module__}.{target.__qualname__}"

    def _is_pyspark_dataframe(self, data: Any) -> bool:
        """Check whether `data` is a pyspark DataFrame (guarded imports)."""
        try:
            import pandera.pyspark  # noqa: F401
            from pyspark.sql import DataFrame as _SparkDataFrame
        except ImportError:
            return False
        return isinstance(data, _SparkDataFrame)

    def _maybe_warn_lazyframe(self, data: Any) -> None:
        """Log a one-time warning when validating a polars `LazyFrame`.

        The flag is not synchronised: concurrent callers can both pass the
        guard, but it only ever moves `False` -> `True` and never affects a
        validation result, so the worst case is a repeated log line.
        """
        if self._lazyframe_warned:
            return
        try:
            import polars as pl
        except ImportError:
            return
        if isinstance(data, pl.LazyFrame):
            self._lazyframe_warned = True
            logger.warning(
                "Validating a polars LazyFrame with pandera: validation depth "
                "may be schema-only (data-level checks require collection)."
            )

    def _validate_pyspark(self, data: Any) -> Any:
        """Validate a pyspark DataFrame; pandera's pyspark backend never raises.

        Failures are reported on the `pandera` accessor of the returned
        DataFrame, so the accessor is read back here. A missing accessor means
        the result cannot be checked at all, while an accessor holding `None`
        means pandera validation is switched off.
        """
        out = self._schema.validate(data)
        accessor = getattr(out, "pandera", _NO_REPORT)
        errors: Any = (
            _NO_REPORT
            if accessor is _NO_REPORT
            else getattr(accessor, "errors", _NO_REPORT)
        )
        if errors is _NO_REPORT:
            raise ValidationConfigurationError(
                f"Could not read pandera's validation report for "
                f"{self._validator_path()}: the object returned by "
                f"'schema.validate()' has no 'pandera.errors' accessor, so "
                f"the result cannot be checked. This usually means the "
                f"installed pandera version is not supported."
            )
        if errors is None:
            logger.warning(
                "pandera returned no validation report for %s: the data was "
                "not validated (pandera validation is disabled).",
                self._validator_path(),
            )
            return out
        if errors:
            failures = [
                CheckFailure(message=f"{category}: {details}")
                for category, details in errors.items()
            ]
            raise DataValidationError(
                f"Pandera validation failed against {self._validator_path()}",
                validator=self._validator_path(),
                failures=failures,
            )
        return out

    def validate(self, data: Any) -> Any:
        """Validate `data` against the configured pandera schema.

        Returns:
            The validated (possibly coerced) data.

        Raises:
            DataValidationError: If validation fails, carrying grouped
                `CheckFailure` objects with capped examples. The original
                pandera error remains available on `__cause__`.
        """
        if self._is_pyspark_dataframe(data):
            return self._validate_pyspark(data)

        self._maybe_warn_lazyframe(data)

        import pandera.errors as pa_errors

        kwargs: dict[str, Any] = {"lazy": self._lazy}
        for name, value in (
            ("head", self._head),
            ("tail", self._tail),
            ("sample", self._sample),
            ("random_state", self._random_state),
        ):
            if value is not None:
                kwargs[name] = value

        try:
            return self._schema.validate(data, **kwargs)
        except pa_errors.SchemaErrors as exc:
            raise DataValidationError(
                f"Pandera validation failed against {self._validator_path()}",
                validator=self._validator_path(),
                failures=_failures_from_schema_errors(exc),
            ) from exc
        except pa_errors.SchemaError as exc:
            raise DataValidationError(
                f"Pandera validation failed against {self._validator_path()}",
                validator=self._validator_path(),
                failures=[_failure_from_schema_error(exc)],
            ) from exc
