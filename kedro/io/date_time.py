"""``DateTime`` is an proxy of the ``datetime`` class that simplifies the
string conversion of datetime objects."""
import re
from datetime import datetime
from datetime import tzinfo as TZInfo
from typing import TYPE_CHECKING, Union

DATETIME_FORMAT = "%Y-%m-%dT%H.%M.%S.%fZ"
FORMAT_CODE_PATTERN = r"%[a-zA-Z]"


class DateTime:
    """A subclass of the ``datetime`` for customizing how it handles string
    conversion."""

    __slots__ = (
        "_datetime",
        "year",
        "month",
        "day",
        "hour",
        "minute",
        "second",
        "microsecond",
    )

    if TYPE_CHECKING:
        _datetime: datetime
        year: int
        month: int
        day: int
        hour: int
        minute: int
        second: int
        microsecond: int
        tzinfo: TZInfo

    def __init__(  # pylint: disable=too-many-arguments
        self,
        year: int,
        month: int,
        day: int,
        hour: int = 0,
        minute: int = 0,
        second: int = 0,
        microsecond: int = 0,
        tzinfo: TZInfo = None,
    ):
        """Initialize a ``DateTime`` object."""
        self._datetime = datetime(
            year, month, day, hour, minute, second, microsecond, tzinfo
        )

    @classmethod
    def from_datetime(cls, timestamp: datetime):
        """Return a ``DateTime`` object from a ``datetime`` object."""
        max_ = datetime.max
        obj = cls(max_.year, max_.month, max_.day)
        obj._datetime = timestamp
        return obj

    def __getattr__(self, name) -> Union[int, "DateTime", TZInfo]:
        """Return the attribute of the underlying datetime object."""
        value = getattr(self._datetime, name)
        if isinstance(value, datetime):
            return self.from_datetime(value)
        return value

    @property
    def datetime(self) -> datetime:
        """Return the datetime object."""
        return self._datetime

    @classmethod
    def max(cls) -> "DateTime":  # type: ignore
        """Return the maximum datetime object."""
        return cls.from_datetime(datetime.max)

    @classmethod
    def min(cls) -> "DateTime":  # type: ignore
        """Return the minimum datetime object."""
        return cls.from_datetime(datetime.min)

    def replace(self, **kwargs) -> "DateTime":
        """Return a ``DateTime`` object with the specified attributes replaced."""
        return self.from_datetime(self._datetime.replace(**kwargs))

    def strftime(self, fmt: str = DATETIME_FORMAT) -> str:
        """Return a string representing the datetime object."""
        microseconds = f"{int(self.microsecond / 1000):03d}"
        pattern = re.sub("%f", microseconds, fmt)
        return self.datetime.strftime(pattern)

    @classmethod
    def strptime(cls, date_string: str, _format: str = DATETIME_FORMAT) -> "DateTime":
        """Return a datetime object from a string representing a datetime."""
        return cls.from_datetime(datetime.strptime(date_string, _format))

    @classmethod
    def partialstrptime(
        cls, date_string: str, _format: str = DATETIME_FORMAT
    ) -> "DateTime":
        """Return a ``DateTime`` object from a string with part of the values
        expected for a format. it will read the format from left to right and
        try to parse the string accordingly. For example, if the format is
        ``%Y-%m-%d`` and the string is ``2018``, it will return a ``DateTime``
        object with year set to 2018, month and day set to 1.

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

    def __str__(self) -> str:
        """Return the Kedro representation of the ``DateTime`` object."""
        return self.strftime(DATETIME_FORMAT)

    def __repr__(self) -> str:
        """Return the string representation of the ``DateTime`` object."""
        return f"{self.__class__.__name__}('{self.__str__()}')"

    def __eq__(self, other) -> bool:
        """Return whether two ``DateTime`` objects are equal."""
        if isinstance(other, DateTime):
            return str(self) == str(other)
        raise NotImplementedError("Can't compare ``DateTime`` with other types")

    def __lt__(self, other) -> bool:
        """Return whether one ``DateTime`` object is less than another."""
        if isinstance(other, DateTime):
            return str(self) < str(other)
        raise NotImplementedError("Cannot compare DateTime with other types")


class UnknownDateTime(DateTime):
    """This class is used to represent a datetime in an unknown granularity."""

    def __init__(self, value: str):
        """Initialize an ``UnknownDateTime`` object."""
        max_ = super().max()
        super().__init__(max_.year, max_.month, max_.day)
        self.value = value

    @classmethod
    def max(cls) -> "UnknownDateTime":
        """Return the maximum datetime object."""
        raise NotImplementedError("UnknownDateTime does not have a maximum value")

    @classmethod
    def min(cls) -> "UnknownDateTime":
        """Return the minimum datetime object."""
        raise NotImplementedError("UnknownDateTime does not have a minimum value")

    def __str__(self) -> str:
        return self.value
