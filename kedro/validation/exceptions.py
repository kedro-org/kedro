"""Custom exceptions for the validation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Bounds that keep a rendered validation error readable no matter how large the
# validated data is; the full backend report stays available on `__cause__`.
# Maximum number of failure examples captured per check.
_MAX_FAILURE_EXAMPLES = 5
# Maximum number of failed checks rendered by `DataValidationError.__str__`.
_MAX_RENDERED_FAILURES = 10
# Maximum length of a rendered failure example.
_MAX_EXAMPLE_REPR_LEN = 40
# Maximum length of a rendered check name, or of the failure message used in
# its place when no check name is available.
_MAX_LABEL_LEN = 200
# Maximum length of a rendered column name.
_MAX_COLUMN_LEN = 60
# Maximum length of the rendered header line and of the fallback message shown
# when an error carries no structured failures.
_MAX_MESSAGE_LEN = 500


class ParameterValidationError(Exception):
    """Raised when parameter validation fails."""

    pass


class ModelInstantiationError(ParameterValidationError):
    """Raised when a typed model fails to instantiate from raw parameters."""

    pass


class ValidationConfigurationError(Exception):
    """Raised when a `validator:` declaration is invalid or unresolvable."""

    pass


@dataclass(frozen=True)
class CheckFailure:
    """A single failed check, optionally grouped over multiple failure cases.

    Attributes are read-only after construction. Instances are not
    hashable, and `failure_examples` is a plain list.

    Attributes:
        message: Human-readable description of the failure.
        check: Name of the failed check (e.g. `greater_than_or_equal_to(0)`).
        column: Column the check applies to, if column-scoped.
        failure_count: Number of failure cases grouped under this check.
        failure_examples: Sample of failing values (capped, default cap 5).
    """

    message: str
    check: str | None = None
    column: str | None = None
    failure_count: int = 1
    failure_examples: list[Any] = field(default_factory=list)


def _truncate(value: Any, limit: int) -> str:
    """Render `value` as a string of at most `limit` characters."""
    text = str(value)
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return text


class DataValidationError(Exception):
    """Raised when dataset validation fails.

    Attributes:
        message: The base error message.
        dataset_name: Name of the dataset that failed validation.
        mode: The operation during which validation failed
            (`"load"`, `"save"` or `"api"`).
        validator: Class path of the validator that raised the failure.
        failures: Structured list of :class:`CheckFailure` objects.

    The rendered message (`str(exc)`) is bounded regardless of the size of
    the validated data; the full backend report remains available on
    `__cause__`.
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
        """Render one grouped check failure as a single bounded line.

        Each part is capped separately so that a long column name still leaves
        room for the check that failed.
        """
        detail = _truncate(failure.check or failure.message, _MAX_LABEL_LEN)
        if failure.column:
            label = f"{_truncate(failure.column, _MAX_COLUMN_LEN)}: {detail}"
        else:
            label = detail
        cases = "case" if failure.failure_count == 1 else "cases"
        line = f"{label} — {failure.failure_count} {cases}"
        if failure.failure_examples:
            examples = ", ".join(
                _truncate(example, _MAX_EXAMPLE_REPR_LEN)
                for example in failure.failure_examples[:_MAX_FAILURE_EXAMPLES]
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
        lines = [_truncate(header, _MAX_MESSAGE_LEN)]
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
            lines.append(_truncate(self.message, _MAX_MESSAGE_LEN))
        return "\n".join(lines)
