"""Tests for tools parsing."""

from __future__ import annotations

import pytest

from kedro.framework.cli.starters import (
    _convert_tool_short_names_to_numbers,
    _parse_tools_input,
    _parse_yes_no_to_bool,
    _validate_tool_selection,
)


class TestParseToolsInput:
    @pytest.mark.parametrize(
        "input,expected",
        [
            ("1", ["1"]),
            ("1,2,3", ["1", "2", "3"]),
            ("2-4", ["2", "3", "4"]),
            ("3-3", ["3"]),
            ("all", ["1", "2", "3", "4", "5", "6"]),
            ("none", []),
        ],
    )
    def test_parse_tools_valid(self, input, expected):
        result = _parse_tools_input(input)
        assert result == expected

    @pytest.mark.parametrize(
        "input",
        ["1-7"],
    )
    def test_validate_range_includes_7(self, input, capsys):
        with pytest.raises(SystemExit):
            _parse_tools_input(input)
        message = "'7' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6.\nKedro Viz is automatically included in the project. Please remove 7 from your tool selection."
        assert message in capsys.readouterr().err

    @pytest.mark.parametrize(
        "input",
        ["5-2", "3-1"],
    )
    def test_parse_tools_invalid_range(self, input, capsys):
        with pytest.raises(SystemExit):
            _parse_tools_input(input)
        message = f"'{input}' is an invalid range for project tools.\nPlease ensure range values go from smaller to larger."
        assert message in capsys.readouterr().err

    @pytest.mark.parametrize(
        "input,right_border",
        [("3-9", "9"), ("3-10000", "10000")],
    )
    def test_parse_tools_range_too_high(self, input, right_border, capsys):
        with pytest.raises(SystemExit):
            _parse_tools_input(input)
        message = f"'{right_border}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."
        assert message in capsys.readouterr().err

    @pytest.mark.parametrize(
        "input,last_invalid",
        [("0,3,5", "0"), ("1,3,8", "8"), ("0-4", "0")],
    )
    def test_parse_tools_invalid_selection(self, input, last_invalid, capsys):
        with pytest.raises(SystemExit):
            selected = _parse_tools_input(input)
            _validate_tool_selection(selected)
        message = f"'{last_invalid}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."
        assert message in capsys.readouterr().err


class TestParseYesNoToBools:
    @pytest.mark.parametrize(
        "input",
        ["yes", "YES", "y", "Y", "yEs"],
    )
    def test_parse_yes_no_to_bool_responds_true(self, input):
        assert _parse_yes_no_to_bool(input) is True

    @pytest.mark.parametrize(
        "input",
        ["no", "NO", "n", "N", "No", ""],
    )
    def test_parse_yes_no_to_bool_responds_false(self, input):
        assert _parse_yes_no_to_bool(input) is False

    def test_parse_yes_no_to_bool_responds_none(self):
        assert _parse_yes_no_to_bool(None) is None


class TestValidateSelection:
    def test_validate_tool_selection_valid(self):
        tools = ["1", "2", "3", "4"]
        assert _validate_tool_selection(tools) is None

    def test_validate_tool_selection_7_tool(self, capsys):
        tools = ["7"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "'7' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6.\nKedro Viz is automatically included in the project. Please remove 7 from your tool selection."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_invalid_single_tool(self, capsys):
        tools = ["8"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_invalid_multiple_tools(self, capsys):
        tools = ["8", "10", "15"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_mix_valid_invalid_tools(self, capsys):
        tools = ["1", "8", "3", "15"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_empty_list(self):
        tools = []
        assert _validate_tool_selection(tools) is None


class TestConvertToolNamesToNumbers:
    def test_convert_tool_short_names_to_numbers_with_valid_tools(self):
        selected_tools = "lint,test,docs"
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == ["1", "2", "4"]

    def test_convert_tool_short_names_to_numbers_with_empty_string(self):
        selected_tools = ""
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == []

    def test_convert_tool_short_names_to_numbers_with_none_string(self):
        selected_tools = "none"
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == []

    def test_convert_tool_short_names_to_numbers_with_all_string(self):
        result = _convert_tool_short_names_to_numbers("all")
        assert result == ["1", "2", "3", "4", "5", "6"]

    def test_convert_tool_short_names_to_numbers_with_mixed_valid_invalid_tools(self):
        selected_tools = "lint,invalid_tool,docs"
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == ["1", "4"]

    def test_convert_tool_short_names_to_numbers_with_whitespace(self):
        selected_tools = " lint , test , docs "
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == ["1", "2", "4"]

    def test_convert_tool_short_names_to_numbers_with_case_insensitive_tools(self):
        selected_tools = "Lint,TEST,Docs"
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == ["1", "2", "4"]

    def test_convert_tool_short_names_to_numbers_with_invalid_tools(self):
        selected_tools = "invalid_tool1,invalid_tool2"
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == []

    def test_convert_tool_short_names_to_numbers_with_duplicates(self):
        selected_tools = "lint,test,tests"
        result = _convert_tool_short_names_to_numbers(selected_tools)
        assert result == ["1", "2"]
