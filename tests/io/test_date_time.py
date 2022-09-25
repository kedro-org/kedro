from datetime import datetime

import pytest

from kedro.io.date_time import DATETIME_FORMAT, DateTime, ProxyDateTime, UnknownDateTime


def assert_datetime_equal(a: datetime, b: datetime):
    assert (
        a.year == b.year
        and a.month == b.month
        and a.day == b.day
        and a.hour == b.hour
        and a.minute == b.minute
        and a.second == b.second
        and a.microsecond == b.microsecond
        and a.tzinfo == b.tzinfo
    )


class TestProxyDateTime:
    def test_proxy(self):
        timestamp = ProxyDateTime.now()
        assert isinstance(timestamp, DateTime)
        assert isinstance(timestamp, ProxyDateTime)
        assert isinstance(timestamp.year, int)
        assert isinstance(timestamp.month, int)
        assert isinstance(timestamp.day, int)
        assert isinstance(timestamp.hour, int)
        assert isinstance(timestamp.minute, int)
        assert isinstance(timestamp.second, int)
        assert isinstance(timestamp.microsecond, int)

    def test_min_equals_original(self):
        original = datetime.min
        new = ProxyDateTime.min()
        assert_datetime_equal(original, new)

    @pytest.mark.freeze_time("2022-09-24 13:37:42.123456")
    def test_now_equals_original(self):
        now = datetime.now()
        new = ProxyDateTime.now()
        assert_datetime_equal(now, new)

    def test_max_equals_original(self):
        original = datetime.max
        new = ProxyDateTime.max()
        assert_datetime_equal(original, new)

    def test_strftime_trimming_microseconds(self):
        timestamp = ProxyDateTime.max().replace(microsecond=123456)
        assert timestamp.strftime("%f") == "123"

    def test_strftime_equals_original(self):
        pattern = "%Y-%m-%d %H:%M:%S %W %w"
        original = datetime.max
        new = ProxyDateTime.max()
        assert original.strftime(pattern) == new.strftime(pattern)

    def test_default_strftime(self):
        min_ = ProxyDateTime.min()
        timestamp = ProxyDateTime.strftime(min_)
        assert timestamp == "1-01-01T00.00.00.000Z"

    def test_str_strftime(self):
        datetime_ = ProxyDateTime(2022, 9, 13, 13, 37, 42, 123456)
        timestamp = str(datetime_)
        assert timestamp == "2022-09-13T13.37.42.123Z"

    def test_strptime(self):
        timestamp = ProxyDateTime.strptime(
            "2022-09-13 13:37:42.123456", "%Y-%m-%d %H:%M:%S.%f"
        )
        assert isinstance(timestamp, DateTime)
        assert timestamp.year == 2022
        assert timestamp.month == 9
        assert timestamp.day == 13
        assert timestamp.hour == 13
        assert timestamp.minute == 37
        assert timestamp.second == 42
        assert timestamp.microsecond == 123456

    def test_default_strptime(self):
        timestamp = ProxyDateTime.strptime("2022-09-13T13.37.42.123Z")
        assert isinstance(timestamp, DateTime)
        assert timestamp.year == 2022
        assert timestamp.month == 9
        assert timestamp.day == 13
        assert timestamp.hour == 13
        assert timestamp.minute == 37
        assert timestamp.second == 42
        assert timestamp.microsecond == 123000

    def test_partialstrptime_year(self):
        timestamp = ProxyDateTime.partialstrptime("2022", "%Y-%m-%d %H:%M:%S.%f")
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(min_.replace(year=timestamp.year), timestamp)

    def test_partialstrptime_year_month(self):
        timestamp = ProxyDateTime.partialstrptime("2022-09", "%Y-%m-%d %H:%M:%S.%f")
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(
            min_.replace(year=timestamp.year, month=timestamp.month), timestamp
        )

    def test_partialstrptime_year_month_day(self):
        timestamp = ProxyDateTime.partialstrptime("2022-09-13", "%Y-%m-%d %H:%M:%S.%f")
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(
            min_.replace(year=timestamp.year, month=timestamp.month, day=timestamp.day),
            timestamp,
        )

    def test_partialstrptime_year_month_day_hour(self):
        timestamp = ProxyDateTime.partialstrptime(
            "2022-09-13 13", "%Y-%m-%d %H:%M:%S.%f"
        )
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(
            min_.replace(
                year=timestamp.year,
                month=timestamp.month,
                day=timestamp.day,
                hour=timestamp.hour,
            ),
            timestamp,
        )

    def test_partialstrptime_year_month_day_hour_minute(self):
        timestamp = ProxyDateTime.partialstrptime(
            "2022-09-13 13:37", "%Y-%m-%d %H:%M:%S.%f"
        )
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(
            min_.replace(
                year=timestamp.year,
                month=timestamp.month,
                day=timestamp.day,
                hour=timestamp.hour,
                minute=timestamp.minute,
            ),
            timestamp,
        )

    def test_partialstrptime_year_month_day_hour_minute_second(self):
        timestamp = ProxyDateTime.partialstrptime(
            "2022-09-13 13:37:42", "%Y-%m-%d %H:%M:%S.%f"
        )
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(
            min_.replace(
                year=timestamp.year,
                month=timestamp.month,
                day=timestamp.day,
                hour=timestamp.hour,
                minute=timestamp.minute,
                second=timestamp.second,
            ),
            timestamp,
        )

    def test_partialstrptime_year_month_day_hour_minute_second_microsecond(self):
        timestamp = ProxyDateTime.partialstrptime(
            "2022-09-13 13:37:42.123456", "%Y-%m-%d %H:%M:%S.%f"
        )
        assert timestamp.year == 2022
        min_ = ProxyDateTime.min()
        assert_datetime_equal(
            min_.replace(
                year=timestamp.year,
                month=timestamp.month,
                day=timestamp.day,
                hour=timestamp.hour,
                minute=timestamp.minute,
                second=timestamp.second,
                microsecond=timestamp.microsecond,
            ),
            timestamp,
        )

    def test_partialstrptime_itself(self):
        constructor = ProxyDateTime(2022, 9, 13, 13, 37, 42, 123456)
        timestamp = ProxyDateTime.partialstrptime(
            "2022-09-13 13:37:42.123456ZZ", "%Y-%m-%d %H:%M:%S.%fZZ"
        )
        assert_datetime_equal(timestamp, constructor)

    def test_partialstrptime_default_format(self):
        constructor = ProxyDateTime(2022, 9, 13, 13, 37, 42, 123000)
        timestamp = ProxyDateTime.partialstrptime("2022-09-13T13.37.42.123Z")
        assert_datetime_equal(timestamp, constructor)

    def test_partialstrptime_no_values(self):
        with pytest.raises(ValueError):
            ProxyDateTime.partialstrptime("")

    def test_partialstrptime_invalid_value(self):
        with pytest.raises(ValueError):
            ProxyDateTime.partialstrptime("20c")

    def test_partialstrptime_invalid_format(self):
        with pytest.raises(ValueError):
            ProxyDateTime.partialstrptime("2022", "-")

    def test_replace(self):
        timestamp = ProxyDateTime.max()
        timestamp = timestamp.replace(year=1990, month=3, day=14)
        assert isinstance(timestamp, DateTime)
        assert timestamp.year == 1990
        assert timestamp.month == 3
        assert timestamp.day == 14

    def test_equal(self):
        a = ProxyDateTime(2022, 9, 13, 13, 37, 42, 123456)
        b = ProxyDateTime(2022, 9, 13, 13, 37, 42, 123456)
        assert a == b
        min_ = ProxyDateTime.max()
        max_ = ProxyDateTime.min()
        assert min_ != max_

    def test_less_than(self):
        min_ = ProxyDateTime.min()
        max_ = ProxyDateTime.max()
        assert min_ < max_

    def test_sort(self):
        min_ = ProxyDateTime.min()
        max_ = ProxyDateTime.max()
        assert sorted([max_, min_]) == [min_, max_]

    def test_repr(self):
        timestamp = ProxyDateTime(2022, 9, 13, 13, 37, 42, 123456)
        assert repr(timestamp) == "ProxyDateTime('2022-09-13T13.37.42.123Z')"


class TestUnknownDateTime:
    def test_unknown_datetime_str(self):
        timestamp = UnknownDateTime("test")
        assert str(timestamp) == "test"

    def test_strftime(self):
        timestamp = UnknownDateTime("test", "pattern")
        assert timestamp.strftime("abc/pattern/def") == "abc/test/def"

    def test_strftime_default_pattern(self):
        timestamp = UnknownDateTime("test", "pattern")
        assert timestamp.strftime("abc/pattern/def") == "abc/test/def"

    def test_strptime(self):
        timestamp = UnknownDateTime.strptime(
            "abc/test/def", "pattern", "abc/pattern/def"
        )
        assert str(timestamp) == "test"

    def test_strptime_default_pattern(self):
        timestamp = UnknownDateTime.strptime(
            "abc/test/def", pattern=f"abc/{DATETIME_FORMAT}/def"
        )
        assert str(timestamp) == "test"

    def test_strptime_not_found(self):
        with pytest.raises(ValueError):
            UnknownDateTime.strptime("abc/test/de", "abc/pattern/def", "pattern")
