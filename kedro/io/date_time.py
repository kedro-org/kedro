"""``DateTime`` is an proxy of the ``datetime`` class that simplifies the
string conversion of datetime objects."""
import itertools
import re
from abc import ABC, abstractmethod
from datetime import datetime
from datetime import tzinfo as TZInfo
from typing import TYPE_CHECKING, Union, cast

DATETIME_FORMAT = "%Y-%m-%dT%H.%M.%S.%fZ"
FORMAT_CODE_PATTERN = r"%[a-zA-Z]"


class DateTime(ABC):
    """``DateTime`` is the base class datetime classes."""

    @abstractmethod
    def strftime(self, format_: str) -> str:
        """Return a string representing ``DateTime``."""
        pass  # pragma: no cover

    @classmethod
    @abstractmethod
    def strptime(cls, date_string: str, format_: str) -> "DateTime":
        """Converts a ``string`` into a ``DateTime`` object."""
        pass  # pragma: no cover

    @abstractmethod
    def __str__(self) -> str:
        """Return the string representation of the ``DateTime`` object.

        Note:
        This method can be implemented using ``strftime``."""
        pass  # pragma: no cover

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


class ProxyDateTime(DateTime):
    """A ``datetime`` proxy for customizing how it handles string conversion."""

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

    if TYPE_CHECKING:  # pragma: no cover
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
        min_ = datetime.min
        obj = cls(min_.year, min_.month, min_.day)
        obj._datetime = timestamp
        return obj

    def __getattr__(self, name: str) -> Union[int, TZInfo]:
        """Return the attribute of the underlying datetime object."""
        value = getattr(self._datetime, name)
        return value

    @property
    def datetime(self) -> datetime:
        """Return the datetime object."""
        return self._datetime

    @classmethod
    def max(cls) -> "ProxyDateTime":  # type: ignore
        """Return the maximum datetime object."""
        return cls.from_datetime(datetime.max)

    @classmethod
    def now(cls, timezone: TZInfo = None) -> "ProxyDateTime":
        """Return the current datetime."""
        return cls.from_datetime(datetime.now(tz=timezone))

    @classmethod
    def min(cls) -> "ProxyDateTime":  # type: ignore
        """Return the minimum datetime object."""
        return cls.from_datetime(datetime.min)

    def replace(self, **kwargs) -> "ProxyDateTime":
        """Return a ``DateTime`` object with the specified attributes replaced."""
        return self.from_datetime(self._datetime.replace(**kwargs))

    def strftime(self, format_: str = DATETIME_FORMAT) -> str:
        """Return a string representing the datetime object."""
        microseconds = f"{int(self.microsecond / 1000):03d}"
        pattern = re.sub("%f", microseconds, format_)
        return self.datetime.strftime(pattern)

    @classmethod
    def strptime(
        cls, date_string: str, format_: str = DATETIME_FORMAT
    ) -> "ProxyDateTime":
        """Return a datetime object from a string representing a datetime."""
        return cls.from_datetime(datetime.strptime(date_string, format_))

    @classmethod
    def partialstrptime(
        cls, date_string: str, format_: str = DATETIME_FORMAT
    ) -> "ProxyDateTime":
        """Return a ``DateTime`` object from a string with part of the values
        expected for a format. it will read the format from left to right and
        try to parse the string accordingly. For example, if the format is
        ``%Y-%m-%d`` and the string is ``2018``, it will return a ``DateTime``
        object with year set to 2018, month and day set to 1.

        Raises:
            ValueError: If the format string contains unsupported format codes,
                or if the date_string and format cannot be matched.
        """
        format_codes = re.finditer(FORMAT_CODE_PATTERN, format_)
        itself = cast(re.Match, re.match(format_, format_))
        for code in itertools.chain(format_codes, [itself]):
            try:
                return cls.strptime(date_string, format_[: code.span()[1]])
            except ValueError:
                pass
        raise ValueError(
            "No format codes found in the format string, or "
            "no matching values found in the string."
        )

    def __str__(self) -> str:
        """Return the Kedro representation of the ``DateTime`` object."""
        return self.strftime(DATETIME_FORMAT)


class UnknownDateTime(DateTime):
    """This class is used to represent a datetime made of unknown symbols."""

    def __init__(self, value: str, format_: str = None):
        """Initialize an ``UnknownDateTime`` object."""
        self.value = value
        self.format = format_ or DATETIME_FORMAT

    def strftime(self, format_: str) -> str:
        """Replaces ``pattern`` in ``format_`` by ``value``."""
        return re.sub(self.format, self.value, format_)

    @classmethod
    def strptime(
        cls,
        date_string: str,
        format_: str = DATETIME_FORMAT,
        pattern: str = DATETIME_FORMAT,
    ) -> "UnknownDateTime":
        """Finds ``format_`` in ``pattern`` and returns the corresponding
        value in ``date_string``."""
        format_pattern = re.sub(format_, "(.*)", pattern)
        timestamp = re.search(format_pattern, date_string)
        if timestamp and timestamp.groups():
            return UnknownDateTime(timestamp[1], format_)
        raise ValueError(
            f"Could not parse ``{date_string}`` with format ``{format_}``"
            f" and pattern ``{pattern}``."
        )

    def __str__(self) -> str:
        return self.value
