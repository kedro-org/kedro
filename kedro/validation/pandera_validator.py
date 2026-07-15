"""Pandera adapter for catalog-native dataset validation.

All pandera imports live inside functions so that pandera remains an optional
dependency of Kedro.

Detection targets pandera's modern (0.30+) namespaces:
``pandera.api.dataframe.model.DataFrameModel`` is the shared base of the
``pandera.pandas``/``pandera.polars``/``pandera.pyspark`` ``DataFrameModel``
classes, and the per-backend ``DataFrameSchema`` container classes are
accepted as instances. The deprecated top-level ``pandera.DataFrameModel``
is deliberately not referenced.
"""

from __future__ import annotations

import inspect
import logging
import math
from typing import Any

from kedro.validation.core import (
    MAX_FAILURE_EXAMPLES,
    CheckFailure,
    DataValidationError,
    ValidationConfigurationError,
)

logger = logging.getLogger(__name__)


def _is_pandera_model(cls: Any) -> bool:
    """Check whether ``cls`` is a pandera ``DataFrameModel`` subclass.

    Uses the shared base class so pandas, polars and pyspark models are all
    detected. Returns ``False`` if pandera is not installed.
    """
    try:
        from pandera.api.dataframe.model import DataFrameModel as _BaseModel
    except ImportError:
        return False
    return inspect.isclass(cls) and issubclass(cls, _BaseModel)


def _is_pandera_schema_instance(obj: Any) -> bool:
    """Check whether ``obj`` is a pandera ``DataFrameSchema`` instance.

    Each backend's container class import is guarded individually as polars
    and pyspark are optional extras of pandera. Returns ``False`` if pandera
    is not installed.
    """
    container_classes: list[type] = []
    try:
        from pandera.api.pandas.container import DataFrameSchema as _PandasSchema

        container_classes.append(_PandasSchema)
    except ImportError:
        pass
    try:
        from pandera.api.polars.container import DataFrameSchema as _PolarsSchema

        container_classes.append(_PolarsSchema)
    except ImportError:
        pass
    try:
        from pandera.api.pyspark.container import DataFrameSchema as _PySparkSchema

        container_classes.append(_PySparkSchema)
    except ImportError:
        pass
    if not container_classes:
        return False
    return isinstance(obj, tuple(container_classes))


def pandera_adapter(obj: Any, options: dict) -> PanderaValidator | None:
    """Adapt a pandera schema object into a ``PanderaValidator``.

    Args:
        obj: The imported object from a validator ``class_path``.
        options: Options from the validator spec, forwarded to
            ``PanderaValidator``.

    Returns:
        A ``PanderaValidator`` when ``obj`` is a pandera ``DataFrameModel``
        subclass or ``DataFrameSchema`` instance, otherwise ``None``
        (including when pandera is not installed).

    Raises:
        ValidationConfigurationError: If ``options`` contains keys not
            supported by ``PanderaValidator``.
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
    """Normalise a backend failure-cases frame into a list of dicts."""
    if failure_cases is None:
        return []
    # pandas DataFrame
    to_dict = getattr(failure_cases, "to_dict", None)
    if to_dict is not None and hasattr(failure_cases, "columns"):
        try:
            return to_dict(orient="records")
        except TypeError:
            pass
    # polars DataFrame
    to_dicts = getattr(failure_cases, "to_dicts", None)
    if to_dicts is not None:
        return to_dicts()
    if isinstance(failure_cases, list):
        return [
            record if isinstance(record, dict) else {"failure_case": record}
            for record in failure_cases
        ]
    return []


def _clean_column(column: Any) -> str | None:
    """Normalise a failure-case column value (may be None or NaN)."""
    if column is None or (isinstance(column, float) and math.isnan(column)):
        return None
    return str(column)


def _failures_from_schema_errors(exc: Exception) -> list[CheckFailure]:
    """Build grouped ``CheckFailure`` objects from a pandera ``SchemaErrors``.

    Failure cases are grouped by ``(column, check)``; each group records its
    total failure count and up to ``MAX_FAILURE_EXAMPLES`` example values.
    """
    records = _failure_cases_records(getattr(exc, "failure_cases", None))
    if not records:
        return [CheckFailure(message=str(exc))]

    grouped: dict[tuple, dict[str, Any]] = {}
    for record in records:
        column = _clean_column(record.get("column"))
        check = record.get("check")
        check = str(check) if check is not None else None
        group = grouped.setdefault(
            (column, check), {"count": 0, "examples": [], "index": None}
        )
        group["count"] += 1
        if len(group["examples"]) < MAX_FAILURE_EXAMPLES:
            group["examples"].append(record.get("failure_case"))
        if group["index"] is None:
            group["index"] = record.get("index")

    failures = []
    for (column, check), group in grouped.items():
        target = f"column '{column}'" if column else "dataframe"
        failures.append(
            CheckFailure(
                message=f"Check '{check}' failed for {target}",
                check=check,
                column=column,
                failure_count=group["count"],
                failure_examples=group["examples"],
                index=group["index"],
            )
        )
    return failures


def _failure_from_schema_error(exc: Exception) -> CheckFailure:
    """Build a single ``CheckFailure`` from a non-lazy pandera ``SchemaError``."""
    records = _failure_cases_records(getattr(exc, "failure_cases", None))
    check = getattr(exc, "check", None)
    column = _clean_column(getattr(getattr(exc, "schema", None), "name", None))
    return CheckFailure(
        message=str(exc),
        check=str(check) if check is not None else None,
        column=column,
        failure_count=max(len(records), 1),
        failure_examples=[
            record.get("failure_case") for record in records[:MAX_FAILURE_EXAMPLES]
        ],
        index=records[0].get("index") if records else None,
    )


class PanderaValidator:
    """Validates data against a pandera schema (model class or schema instance).

    Supports pandas and polars frames via ``schema.validate`` and pyspark
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
            schema: A pandera ``DataFrameModel`` subclass or
                ``DataFrameSchema`` instance.
            lazy: Collect all failures before raising (default ``True``).
            head: Validate only the first ``head`` rows.
            tail: Validate only the last ``tail`` rows.
            sample: Validate a random sample of ``sample`` rows.
            random_state: Seed for ``sample``.
        """
        self._schema = schema
        self._lazy = lazy
        self._head = head
        self._tail = tail
        self._sample = sample
        self._random_state = random_state
        self._lazyframe_warned = False

    def _validator_path(self) -> str:
        """Dotted path of the schema class for error reporting."""
        target = self._schema if inspect.isclass(self._schema) else type(self._schema)
        return f"{target.__module__}.{target.__qualname__}"

    def _is_pyspark_dataframe(self, data: Any) -> bool:
        """Check whether ``data`` is a pyspark DataFrame (guarded imports)."""
        try:
            import pandera.pyspark  # noqa: F401
            from pyspark.sql import DataFrame as _SparkDataFrame
        except ImportError:
            return False
        return isinstance(data, _SparkDataFrame)

    def _maybe_warn_lazyframe(self, data: Any) -> None:
        """Log a one-time warning when validating a polars ``LazyFrame``."""
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
        """Validate a pyspark DataFrame; pandera's pyspark backend never raises."""
        out = self._schema.validate(data)
        errors = getattr(getattr(out, "pandera", None), "errors", None)
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
        """Validate ``data`` against the configured pandera schema.

        Returns:
            The validated (possibly coerced) data.

        Raises:
            DataValidationError: If validation fails, carrying grouped
                ``CheckFailure`` objects with capped examples. The original
                pandera error remains available on ``__cause__``.
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
