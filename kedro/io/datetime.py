"""``DateTime`` is an inheritance of the ``datetime`` class that simplifies the
string conversion of datetime objects."""
import re
from datetime import datetime
from typing import TYPE_CHECKING, cast

DATETIME_FORMAT = "%Y-%m-%dT%H.%M.%S.%fZ"
FORMAT_CODE_PATTERN = r"%[a-zA-Z]"


class DateTime(datetime):
    """A subclass of the ``datetime`` for customizing how it handles string
    conversion."""

    def strftime(self, fmt: str = DATETIME_FORMAT) -> str:
        """Return a string representing the datetime object."""
        microseconds = f"{int(self.microsecond / 1000):03d}"
        pattern = re.sub("%f", microseconds, fmt)
        return super().strftime(pattern)

    @classmethod
    def partialstrptime(
        cls, date_string: str, _format: str = DATETIME_FORMAT
    ) -> "DateTime":
        """Return a ``DateTime`` object from a string with a partial format.
        it will read the format from left to right and try to parse the string
        accordingly. For example, if the format is ``%Y-%m-%d`` and the string
        is ``2018``, it will return a ``DateTime`` object with year set to
        2018, month and day set to 1.

        Raises:
            ValueError: If the format string contains unsupported format codes,
                or if the date_string and format cannot be matched.
        """
        value_pattern = re.sub(FORMAT_CODE_PATTERN, r"(\\d+)", _format)
        format_codes = re.findall(FORMAT_CODE_PATTERN, _format)
        values = re.search(value_pattern, date_string)

        if not values:
            raise ValueError(
                "No format codes found in the format string, or "
                "no matching values found in the string."
            )

        new_format, new_date_string = "", ""
        for code, value in zip(format_codes, values.groups()):
            new_format += f"-{code}"
            new_date_string += f"-{value}"

        return cls.strptime(new_date_string, new_format)

    @classmethod
    def strptime(cls, date_string: str, _format: str = DATETIME_FORMAT) -> "DateTime":
        """Return a datetime object from a string representing a datetime."""
        return cast(DateTime, super().strptime(date_string, _format))

    def __str__(self) -> str:
        """Return the Kedro representation of the datetime object."""
        return self.strftime(DATETIME_FORMAT)

    def __repr__(self) -> str:
        """Return the string representation of the datetime object."""
        return f"{self.__class__.__name__}('{self.__str__()}')"

    def __eq__(self, other) -> bool:
        """Return whether two datetime objects are equal."""
        if isinstance(other, DateTime):
            return str(self) == str(other)
        raise NotImplementedError("Can't compare ``DateTime`` with other types")

    def __lt__(self, other) -> bool:
        """Return whether one datetime object is less than another."""
        if isinstance(other, DateTime):
            return str(self) < str(other)
        raise NotImplementedError("Cannot compare DateTime with other types")


class UnknownDateTime(DateTime):
    """This class is used to represent a datetime in an unknown granularity."""

    __slots__ = ("value",)

    if TYPE_CHECKING:
        value: str

    def __new__(cls, value: str):  # pylint: disable=W0222
        min_ = cls.min
        obj = super().__new__(cls, min_.year, min_.month, min_.day)
        obj.value = value
        return obj

    def __str__(self) -> str:
        return self.value
