"""Tests for kedro.validation.exceptions."""

from __future__ import annotations

import pytest

from kedro.validation.exceptions import (
    CheckFailure,
    DataValidationError,
    ModelInstantiationError,
    ParameterValidationError,
)


class TestParameterValidationError:
    def test_basic_error(self):
        error = ParameterValidationError("something failed")
        assert str(error) == "something failed"

    def test_is_exception(self):
        error = ParameterValidationError("bad")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ParameterValidationError, match="param error"):
            raise ParameterValidationError("param error")


class TestModelInstantiationError:
    def test_basic_error(self):
        error = ModelInstantiationError("failed to instantiate")
        assert str(error) == "failed to instantiate"

    def test_is_parameter_validation_error_subclass(self):
        error = ModelInstantiationError("failed")
        assert isinstance(error, ParameterValidationError)

    def test_can_be_caught_as_parameter_validation_error(self):
        with pytest.raises(ParameterValidationError):
            raise ModelInstantiationError("model failed")


class TestErrorRenderingEdgeCases:
    def test_long_example_is_truncated(self):
        failure = CheckFailure(
            message="m", check="c", column="col", failure_examples=["x" * 100]
        )
        text = str(DataValidationError("boom", dataset_name="ds", failures=[failure]))
        assert "..." in text
        assert "x" * 100 not in text

    def test_label_variants(self):
        f_check_only = CheckFailure(message="m1", check="only_check")
        f_column_only = CheckFailure(message="m2", column="only_col")
        f_message_only = CheckFailure(message="only_message")
        text = str(
            DataValidationError(
                "boom",
                dataset_name="ds",
                failures=[f_check_only, f_column_only, f_message_only],
            )
        )
        assert "only_check" in text
        assert "only_col: m2" in text
        assert "only_message" in text

    def test_without_dataset_name_message_is_the_header(self):
        assert str(DataValidationError("standalone message")) == "standalone message"

    def test_empty_message_without_dataset_name_falls_back(self):
        assert str(DataValidationError("")) == "Validation failed"

    def test_long_header_is_truncated(self):
        text = str(DataValidationError("x" * 600))
        assert len(text.splitlines()[0]) <= 500

    def test_message_shown_and_truncated_when_no_failures(self):
        err = DataValidationError("detail " * 100, dataset_name="ds")
        text = str(err)
        assert text.startswith("Validation failed for dataset 'ds'")
        assert text.endswith("...")

    @pytest.mark.parametrize(
        "failure",
        [
            CheckFailure(message="m", check="c" * 5000, column="col"),
            CheckFailure(message="m", check="c" * 5000),
            CheckFailure(message="m" * 5000, column="col"),
            CheckFailure(message="m" * 5000),
            CheckFailure(message="m", check="c", column="col" * 5000),
            CheckFailure(
                message="m",
                check="c" * 5000,
                column="col" * 5000,
                failure_examples=["e" * 500] * 5,
            ),
        ],
        ids=[
            "column+check",
            "check",
            "column+message",
            "message",
            "long-column",
            "everything-long",
        ],
    )
    def test_rendered_lines_have_bounded_length(self, failure):
        # A check name can carry a whole allowed-value list (e.g. isin([...]))
        # and a message can carry a backend report. The worst case is
        # 60 (column) + 200 (label) + 5 x 40 (examples) + separators.
        text = str(DataValidationError("boom", dataset_name="ds", failures=[failure]))
        assert all(len(line) <= 550 for line in text.splitlines())

    def test_long_column_does_not_crowd_out_the_check(self):
        failure = CheckFailure(message="m", check="the_check", column="c" * 5000)
        text = str(DataValidationError("boom", dataset_name="ds", failures=[failure]))
        assert "the_check" in text

    def test_rendering_caps_number_of_checks(self):
        failures = [
            CheckFailure(message=f"check {i}", check=f"check_{i}", failure_count=1)
            for i in range(25)
        ]
        exc = DataValidationError(
            "boom", dataset_name="companies", mode="load", failures=failures
        )
        rendered = str(exc)
        assert "25 check(s) failed" in rendered
        assert "... and 15 more check(s)" in rendered
        assert len(rendered.splitlines()) < 20
