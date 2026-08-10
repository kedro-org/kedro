"""Core primitives for catalog-native dataset validation.

This module defines the `Validator` protocol, the `ValidatorSpec`
configuration model for the catalog `validator:` key, the exceptions raised
by the validation funnel and the `resolve_validator` factory that turns a
spec into a ready-to-use validator instance.

No third-party validation backend (e.g. pandera) is imported at module level;
backend adapters are imported lazily so that the backends remain optional
dependencies.
"""

from __future__ import annotations

import importlib.util
import inspect
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from kedro.utils import load_obj
from kedro.validation.exceptions import (
    DataValidationError,  # noqa: F401  (re-exported for backwards-compatible imports)
    ValidationConfigurationError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

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

_PANDERA_INSTALL_HINT = (
    "Install it with: pip install 'kedro[pandera-pandas]' "
    "(or the pandera-polars extra for the polars backend)."
)


@runtime_checkable
class Validator(Protocol):
    """Protocol that all dataset validators must satisfy.

    A validator receives the in-memory data of a dataset and either returns it
    (possibly transformed, e.g. dtype-coerced) or raises to signal failure.
    """

    def validate(self, data: Any) -> Any:
        """Validate `data` and return the (possibly transformed) data.

        ANY exception raised by this method is treated as a validation
        failure. Implementations may be called concurrently and must therefore
        be thread-safe or stateless.
        """


def _parse_on_modes(value: Any, ds_name: str) -> tuple[str, ...]:
    """Normalise and validate the `on` field of a validator declaration."""
    if isinstance(value, str):
        on = (value,)
    elif isinstance(value, list | tuple):
        on = tuple(value)
    else:
        on = (value,)
    if not on or not all(mode in _VALID_MODES for mode in on):
        raise ValidationConfigurationError(
            f"Invalid validator declaration for dataset '{ds_name}': "
            f"'on' must be a non-empty subset of {list(_VALID_MODES)}, "
            f"got {value!r}."
        )
    # Canonicalise so every declaration has one representation: deduplicated,
    # in ("load", "save") order.
    return tuple(mode for mode in _VALID_MODES if mode in on)


@dataclass(frozen=True)
class ValidatorSpec:
    """Parsed representation of a catalog `validator:` declaration.

    Attributes:
        class_path: Dotted import path of the validator object.
        on: Modes the validator applies to; subset of `("load", "save")`.
        severity: `"error"` (raise on failure) or `"warn"` (log only).
        enabled: Whether the validator is active in the catalog funnel.
        skip_load_after_save: Skip load-validation when the same catalog
            instance already validated the dataset on save in this process.
        options: Keyword options forwarded to the validator/adapter.

    Attributes are read-only after construction. Instances are not hashable,
    and `options` is a plain dict, copied at parse time.
    """

    class_path: str
    on: tuple[str, ...] = ("load", "save")
    severity: str = "error"
    enabled: bool = True
    skip_load_after_save: bool = False
    options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dataset_config(cls, ds_name: str, config: Any) -> ValidatorSpec:
        """Build a spec from a catalog `validator:` value.

        Accepts a plain string (shorthand class path) or a dictionary
        (long form with keys `class`, `on`, `severity`, `enabled`,
        `skip_load_after_save` and `options`).

        Args:
            ds_name: Name of the dataset declaring the validator (used in
                error messages).
            config: The raw `validator:` value from the catalog config.

        Returns:
            The parsed `ValidatorSpec`.

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

        # YAML 1.1 reads an unquoted `on` key as the boolean True, not the
        # string "on" (https://yaml.org/type/bool.html), so `on: [load, save]`
        # arrives here as `{True: [...]}`. Map it back so the unquoted form
        # works. The identity test matters: `True in config` is also satisfied
        # by an integer key `1`, since `True == 1` and `hash(True) == hash(1)`.
        if any(key is True for key in config):
            if "on" in config:
                raise ValidationConfigurationError(
                    f"Invalid validator declaration for dataset '{ds_name}': "
                    f"both an unquoted 'on' key (which YAML reads as the "
                    f'boolean True) and a quoted "on" key are present, and '
                    f"only one of them can take effect. Keep a single 'on' key."
                )
            config = {("on" if key is True else key): v for key, v in config.items()}

        # Sort by `repr` so the comparison stays total: YAML can supply
        # non-string keys (e.g. `1:`, or an unquoted `off:` which reads as the
        # boolean False), which are not orderable against string keys.
        unknown_keys = sorted(set(config) - set(_ALLOWED_SPEC_KEYS), key=repr)
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

        on = _parse_on_modes(config.get("on", _VALID_MODES), ds_name)

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

        for flag_name in ("enabled", "skip_load_after_save"):
            if flag_name in config and not isinstance(config[flag_name], bool):
                raise ValidationConfigurationError(
                    f"Invalid validator declaration for dataset '{ds_name}': "
                    f"'{flag_name}' must be a boolean, "
                    f"got {type(config[flag_name]).__name__}."
                )

        enabled = config.get("enabled", True)
        skip_load_after_save = config.get("skip_load_after_save", False)

        return cls(
            class_path=class_path,
            on=on,
            severity=severity,
            enabled=enabled,
            skip_load_after_save=skip_load_after_save,
            # Copy so the spec never aliases the catalog configuration it was
            # parsed from, and cannot mutate it later through `options`.
            options=dict(options),
        )

    def to_config(self) -> str | dict[str, Any]:
        """Serialise the spec back to its catalog configuration shape.

        Returns:
            The plain class path string when the spec is equivalent to the
            shorthand form, otherwise a dictionary containing `class` plus
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
    """Wraps a plain callable `fn(data) -> data-or-raise` as a validator.

    If the wrapped callable returns `None` (assertion-style validators),
    the original data is returned unchanged.
    """

    def __init__(self, func: Callable[[Any], Any]) -> None:
        self._func = func

    def validate(self, data: Any) -> Any:
        """Call the wrapped function; any raise is a validation failure."""
        result = self._func(data)
        return data if result is None else result

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._func!r})"


def _import_error_hint(missing: str) -> str:
    """Build a hint for a failed validator import.

    `missing` is the module or attribute name that Python reported as
    unresolvable when the import failed (empty when it reported none).
    """
    if missing == "pandera" or (
        missing.startswith("pandera.") and importlib.util.find_spec("pandera") is None
    ):
        return f"The 'pandera' package is not installed. {_PANDERA_INSTALL_HINT}"
    if missing.startswith("pandera."):
        return (
            f"pandera is installed but '{missing}' could not be imported; "
            f"check the class path."
        )
    return (
        "Check that the class path is correct and the package is "
        "installed in the current environment."
    )


def resolve_validator(spec: ValidatorSpec) -> Validator:
    """Resolve a `ValidatorSpec` into a usable validator instance.

    Resolution order:

    1. Import the object at `spec.class_path`.
    2. Offer the object to backend adapters (currently pandera); the first
       adapter returning non-`None` wins.
    3. If the object is a class, instantiate it with `spec.options` and
       require the instance to satisfy the `Validator` protocol.
    4. If the object is already a `Validator` instance, return it
       (`options` must be empty).
    5. If the object is a plain callable, wrap it in `CallableValidator`
       (`options` must be empty).

    Args:
        spec: The validator spec to resolve.

    Returns:
        An object satisfying the `Validator` protocol.

    Raises:
        ValidationConfigurationError: If the object cannot be imported or
            does not resolve to a valid validator.
    """
    try:
        obj = load_obj(spec.class_path)
    except (ImportError, AttributeError, ValueError) as exc:
        hint = _import_error_hint(getattr(exc, "name", "") or "")
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
        # Reject before constructing anything: instantiating an arbitrary
        # class just to discover it is not a validator can have side effects.
        if not callable(getattr(obj, "validate", None)):
            raise ValidationConfigurationError(
                f"Validator '{spec.class_path}' resolved to class "
                f"{obj.__name__}, which does not provide a 'validate(data)' "
                f"method."
            )
        # NEVER isinstance-check the class object itself against the
        # runtime-checkable Protocol: it matches any class merely defining
        # a `validate` method and would return the uninstantiated class,
        # silently dropping options.
        try:
            instance = obj(**spec.options)
        except Exception as exc:
            # Constructors are free to validate their own arguments with any
            # exception type; all of them are configuration errors here.
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
                f"accept options {sorted(spec.options, key=repr)}; declare a "
                f"class path instead or drop the options."
            )
        return obj

    if callable(obj):
        if spec.options:
            raise ValidationConfigurationError(
                f"Validator '{spec.class_path}' is a plain callable and "
                f"cannot accept options {sorted(spec.options, key=repr)}; "
                f"declare a validator class that takes them as constructor "
                f"arguments, or drop the options."
            )
        return CallableValidator(obj)

    raise ValidationConfigurationError(
        f"Validator '{spec.class_path}' resolved to "
        f"{type(obj).__name__} ({obj!r}), which is not a validator class, "
        f"a validator instance, a supported schema or a callable."
    )


def preflight_check(specs: dict[str, ValidatorSpec]) -> list[str]:
    """Check that the packages backing declared validators are importable.

    Only the top-level package of each `class_path` is checked, via
    `importlib.util.find_spec` (no module execution).

    Args:
        specs: Mapping of dataset names to their validator specs.

    Returns:
        A list of warning strings, one per dataset whose validator's
        top-level package cannot be found. Nothing is logged here; the
        caller decides how to emit them.
    """
    messages: list[str] = []
    for ds_name, spec in specs.items():
        top_level = spec.class_path.split(".")[0]
        if not top_level:
            messages.append(
                f"Validator for dataset '{ds_name}' has an invalid class "
                f"path {spec.class_path!r}."
            )
            continue
        try:
            found = importlib.util.find_spec(top_level)
        except (ImportError, ValueError):
            found = None
        if found is None:
            hint = f" {_PANDERA_INSTALL_HINT}" if top_level == "pandera" else ""
            messages.append(
                f"Validator for dataset '{ds_name}' requires package "
                f"'{top_level}' which is not installed "
                f"(declared: {spec.class_path}).{hint}"
            )
    return messages
