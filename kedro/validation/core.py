"""Core primitives for catalog-native dataset validation.

This module defines the ``Validator`` protocol, the ``ValidatorSpec``
configuration model for the catalog ``validator:`` key, the exceptions raised
by the validation funnel and the ``resolve_validator`` factory that turns a
spec into a ready-to-use validator instance.

No third-party validation backend (e.g. pandera) is imported at module level;
backend adapters are imported lazily so that the backends remain optional
dependencies.
"""

from __future__ import annotations

import importlib.util
import inspect
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from kedro.utils import load_obj

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

_ALLOWED_SPEC_KEYS = (
    "class",
    "on",
    "severity",
    "enabled",
    "skip_load_after_save",
    "options",
)
_VALID_MODES = ("load", "save")
_VALID_SEVERITIES = ("error", "warn")

#: Maximum number of failure examples captured per check.
MAX_FAILURE_EXAMPLES = 5
#: Maximum number of failed checks rendered by ``DataValidationError.__str__``.
_MAX_RENDERED_FAILURES = 10
#: Maximum length of a rendered failure example.
_MAX_EXAMPLE_REPR_LEN = 40
#: Maximum length of a rendered fallback message.
_MAX_MESSAGE_LEN = 500


@runtime_checkable
class Validator(Protocol):
    """Protocol that all dataset validators must satisfy.

    A validator receives the in-memory data of a dataset and either returns it
    (possibly transformed, e.g. dtype-coerced) or raises to signal failure.
    """

    def validate(self, data: Any) -> Any:
        """Validate ``data`` and return the (possibly transformed) data.

        ANY exception raised by this method is treated as a validation
        failure. Implementations may be called concurrently and must therefore
        be thread-safe or stateless.
        """
        ...


@dataclass(frozen=True)
class CheckFailure:
    """A single failed check, optionally grouped over multiple failure cases.

    Attributes:
        message: Human-readable description of the failure.
        check: Name of the failed check (e.g. ``greater_than_or_equal_to(0)``).
        column: Column the check applies to, if column-scoped.
        failure_count: Number of failure cases grouped under this check.
        failure_examples: Sample of failing values (capped, default cap 5).
        index: Index/location of the first failure case, if available.
    """

    message: str
    check: str | None = None
    column: str | None = None
    failure_count: int = 1
    failure_examples: list = field(default_factory=list)
    index: Any | None = None


def _render_example(value: Any) -> str:
    """Render a failure example value, bounded in length."""
    text = str(value)
    if len(text) > _MAX_EXAMPLE_REPR_LEN:
        text = text[: _MAX_EXAMPLE_REPR_LEN - 3] + "..."
    return text


class DataValidationError(Exception):
    """Raised when dataset validation fails.

    Attributes:
        message: The base error message.
        dataset_name: Name of the dataset that failed validation.
        mode: The operation during which validation failed
            (``"load"``, ``"save"`` or ``"api"``).
        validator: Class path of the validator that raised the failure.
        failures: Structured list of :class:`CheckFailure` objects.

    The rendered message (``str(exc)``) is bounded regardless of the size of
    the validated data; the full backend report remains available on
    ``__cause__``.
    """

    def __init__(
        self,
        message: str,
        *,
        dataset_name: str | None = None,
        mode: str | None = None,
        validator: str | None = None,
        failures: list[CheckFailure] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.dataset_name = dataset_name
        self.mode = mode
        self.validator = validator
        self.failures: list[CheckFailure] = list(failures) if failures else []

    @staticmethod
    def _render_failure(failure: CheckFailure) -> str:
        """Render one grouped check failure as a single bounded line."""
        if failure.column and failure.check:
            label = f"{failure.column}: {failure.check}"
        elif failure.check:
            label = failure.check
        elif failure.column:
            label = f"{failure.column}: {failure.message}"
        else:
            label = failure.message
        cases = "case" if failure.failure_count == 1 else "cases"
        line = f"{label} — {failure.failure_count} {cases}"
        if failure.failure_examples:
            examples = ", ".join(
                _render_example(example)
                for example in failure.failure_examples[:MAX_FAILURE_EXAMPLES]
            )
            line += f" (e.g. {examples})"
        return line

    def __str__(self) -> str:
        if self.dataset_name:
            header = f"Validation failed for dataset '{self.dataset_name}'"
            if self.mode:
                header += f" on {self.mode}"
        else:
            header = self.message or "Validation failed"
        if len(header) > _MAX_MESSAGE_LEN:
            header = header[: _MAX_MESSAGE_LEN - 3] + "..."
        lines = [header]
        if self.validator:
            lines.append(f"(validator: {self.validator})")
        if self.failures:
            total_cases = sum(failure.failure_count for failure in self.failures)
            lines.append(
                f"{len(self.failures)} check(s) failed — "
                f"{total_cases} failure case(s):"
            )
            for failure in self.failures[:_MAX_RENDERED_FAILURES]:
                lines.append(f"  - {self._render_failure(failure)}")
            hidden = len(self.failures) - _MAX_RENDERED_FAILURES
            if hidden > 0:
                lines.append(f"  ... and {hidden} more check(s)")
        elif self.dataset_name and self.message:
            message = self.message
            if len(message) > _MAX_MESSAGE_LEN:
                message = message[: _MAX_MESSAGE_LEN - 3] + "..."
            lines.append(message)
        return "\n".join(lines)


class ValidationConfigurationError(Exception):
    """Raised when a ``validator:`` declaration is invalid or unresolvable."""

    pass


@dataclass(frozen=True)
class ValidatorSpec:
    """Parsed representation of a catalog ``validator:`` declaration.

    Attributes:
        class_path: Dotted import path of the validator object.
        on: Modes the validator applies to; subset of ``("load", "save")``.
        severity: ``"error"`` (raise on failure) or ``"warn"`` (log only).
        enabled: Whether the validator is active in the catalog funnel.
        skip_load_after_save: Skip load-validation when the same catalog
            instance already validated the dataset on save in this process.
        options: Keyword options forwarded to the validator/adapter.
    """

    class_path: str
    on: tuple = ("load", "save")
    severity: str = "error"
    enabled: bool = True
    skip_load_after_save: bool = False
    options: dict = field(default_factory=dict)

    @classmethod
    def from_config(cls, ds_name: str, config: Any) -> ValidatorSpec:
        """Build a spec from a catalog ``validator:`` value.

        Accepts a plain string (shorthand class path) or a dictionary
        (long form with keys ``class``, ``on``, ``severity``, ``enabled``,
        ``skip_load_after_save`` and ``options``).

        Args:
            ds_name: Name of the dataset declaring the validator (used in
                error messages).
            config: The raw ``validator:`` value from the catalog config.

        Returns:
            The parsed ``ValidatorSpec``.

        Raises:
            ValidationConfigurationError: If the declaration is malformed.
        """
        if isinstance(config, str):
            return cls(class_path=config)

        if isinstance(config, list):
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"list form is reserved for future use. Declare a single "
                f"validator as a class path string or a dictionary."
            )

        if not isinstance(config, dict):
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"expected a class path string or a dictionary, got "
                f"{type(config).__name__} ({config!r})."
            )

        if True in config:
            # YAML 1.1 parses an unquoted `on` key as boolean True
            # (the "Norway problem"). Normalise it back so users can write
            # `on: [load, save]` without quoting the key.
            config = {("on" if k is True else k): v for k, v in config.items()}

        unknown_keys = sorted(set(config) - set(_ALLOWED_SPEC_KEYS))
        if unknown_keys:
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"unknown key(s) {unknown_keys}. Allowed keys: "
                f"{sorted(_ALLOWED_SPEC_KEYS)}."
            )

        class_path = config.get("class")
        if not isinstance(class_path, str) or not class_path:
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"'class' must be a non-empty class path string."
            )

        on = config.get("on", _VALID_MODES)
        if isinstance(on, str):
            on = (on,)
        elif isinstance(on, list | tuple):
            on = tuple(on)
        else:
            on = (on,)
        if not on or not all(mode in _VALID_MODES for mode in on):
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"'on' must be a non-empty subset of {list(_VALID_MODES)}, "
                f"got {config.get('on')!r}."
            )

        severity = config.get("severity", "error")
        if severity not in _VALID_SEVERITIES:
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"'severity' must be one of {list(_VALID_SEVERITIES)}, "
                f"got {severity!r}."
            )

        options = config.get("options", {})
        if not isinstance(options, dict):
            raise ValidationConfigurationError(
                f"Invalid validator declaration for dataset '{ds_name}': "
                f"'options' must be a dictionary, got {type(options).__name__}."
            )

        return cls(
            class_path=class_path,
            on=on,
            severity=severity,
            enabled=bool(config.get("enabled", True)),
            skip_load_after_save=bool(config.get("skip_load_after_save", False)),
            options=dict(options),
        )

    def to_config(self) -> str | dict[str, Any]:
        """Serialise the spec back to its catalog configuration shape.

        Returns:
            The plain class path string when the spec is equivalent to the
            shorthand form, otherwise a dictionary containing ``class`` plus
            every non-default field.
        """
        config: dict[str, Any] = {}
        if tuple(self.on) != _VALID_MODES:
            config["on"] = list(self.on)
        if self.severity != "error":
            config["severity"] = self.severity
        if not self.enabled:
            config["enabled"] = self.enabled
        if self.skip_load_after_save:
            config["skip_load_after_save"] = self.skip_load_after_save
        if self.options:
            config["options"] = dict(self.options)
        if not config:
            return self.class_path
        return {"class": self.class_path, **config}


class CallableValidator:
    """Wraps a plain callable ``fn(data) -> data-or-raise`` as a validator.

    If the wrapped callable returns ``None`` (assertion-style validators),
    the original data is returned unchanged.
    """

    def __init__(self, func: Callable[[Any], Any]) -> None:
        self._func = func

    def validate(self, data: Any) -> Any:
        """Call the wrapped function; any raise is a validation failure."""
        result = self._func(data)
        return data if result is None else result


def resolve_validator(spec: ValidatorSpec) -> Validator:
    """Resolve a ``ValidatorSpec`` into a usable validator instance.

    Resolution order:

    1. Import the object at ``spec.class_path``.
    2. Offer the object to backend adapters (currently pandera); the first
       adapter returning non-``None`` wins.
    3. If the object is a class, instantiate it with ``spec.options`` and
       require the instance to satisfy the ``Validator`` protocol.
    4. If the object is already a ``Validator`` instance, return it
       (``options`` must be empty).
    5. If the object is a plain callable, wrap it in ``CallableValidator``
       (``options`` must be empty).

    Args:
        spec: The validator spec to resolve.

    Returns:
        An object satisfying the ``Validator`` protocol.

    Raises:
        ValidationConfigurationError: If the object cannot be imported or
            does not resolve to a valid validator.
    """
    try:
        obj = load_obj(spec.class_path)
    except (ImportError, AttributeError) as exc:
        hint = (
            "Check that the class path is correct and the package is "
            "installed in the current environment."
        )
        missing = getattr(exc, "name", "") or ""
        if missing.split(".")[0] == "pandera":
            hint = (
                "The 'pandera' package is not installed. "
                "Install it with: pip install kedro[validation]"
            )
        raise ValidationConfigurationError(
            f"Could not import validator '{spec.class_path}': {exc}. {hint}"
        ) from exc

    # Adapters are imported lazily so validation backends stay optional.
    from kedro.validation.pandera_validator import pandera_adapter

    _adapters = [pandera_adapter]
    for adapt in _adapters:
        result = adapt(obj, spec.options)
        if result is not None:
            return result

    if inspect.isclass(obj):
        # NEVER isinstance-check the class object itself against the
        # runtime-checkable Protocol: it matches any class merely defining
        # a `validate` method and would return the uninstantiated class,
        # silently dropping options.
        try:
            instance = obj(**spec.options)
        except TypeError as exc:
            raise ValidationConfigurationError(
                f"Could not instantiate validator '{spec.class_path}' with "
                f"options {spec.options!r}: {exc}"
            ) from exc
        if isinstance(instance, Validator):
            return instance
        raise ValidationConfigurationError(
            f"Validator '{spec.class_path}' was instantiated but does not "
            f"provide a 'validate(data)' method."
        )

    if isinstance(obj, Validator):
        if spec.options:
            raise ValidationConfigurationError(
                f"Validator '{spec.class_path}' is an instance and cannot "
                f"accept options {sorted(spec.options)}; declare a class "
                f"path instead or drop the options."
            )
        return obj

    if callable(obj):
        if spec.options:
            raise ValidationConfigurationError(
                f"Validator '{spec.class_path}' is a plain callable and "
                f"cannot accept options {sorted(spec.options)}."
            )
        return CallableValidator(obj)

    raise ValidationConfigurationError(
        f"Validator '{spec.class_path}' resolved to "
        f"{type(obj).__name__} ({obj!r}), which is not a validator class, "
        f"a validator instance, a supported schema or a callable."
    )


def preflight_check(specs: dict[str, ValidatorSpec]) -> list[str]:
    """Check that the packages backing declared validators are importable.

    Only the top-level package of each ``class_path`` is checked, via
    ``importlib.util.find_spec`` (no module execution).

    Args:
        specs: Mapping of dataset names to their validator specs.

    Returns:
        A list of warning strings, one per dataset whose validator's
        top-level package cannot be found.
    """
    warnings: list[str] = []
    for ds_name, spec in specs.items():
        top_level = spec.class_path.split(".")[0]
        try:
            found = importlib.util.find_spec(top_level)
        except (ImportError, ValueError):
            found = None
        if found is None:
            hint = ""
            if top_level == "pandera":
                hint = " Install it with: pip install kedro[validation]."
            warnings.append(
                f"Validator for dataset '{ds_name}' requires package "
                f"'{top_level}' which is not installed "
                f"(declared: {spec.class_path}).{hint}"
            )
    return warnings
