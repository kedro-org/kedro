"""Tests for ``ValidatorSpec`` parsing and serialisation (KEP-7 v2)."""

from __future__ import annotations

import pytest

from kedro.validation import ValidationConfigurationError, ValidatorSpec


class TestFromConfigShorthand:
    def test_string_shorthand(self):
        spec = ValidatorSpec.from_config("companies", "my_pkg.schemas.CompaniesSchema")

        assert spec.class_path == "my_pkg.schemas.CompaniesSchema"
        assert spec.on == ("load", "save")
        assert spec.severity == "error"
        assert spec.enabled is True
        assert spec.skip_load_after_save is False
        assert spec.options == {}


class TestFromConfigLongForm:
    def test_full_long_form(self):
        spec = ValidatorSpec.from_config(
            "companies",
            {
                "class": "my_pkg.schemas.CompaniesSchema",
                "on": ["save"],
                "severity": "warn",
                "enabled": False,
                "skip_load_after_save": True,
                "options": {"lazy": False},
            },
        )

        assert spec.class_path == "my_pkg.schemas.CompaniesSchema"
        assert spec.on == ("save",)
        assert spec.severity == "warn"
        assert spec.enabled is False
        assert spec.skip_load_after_save is True
        assert spec.options == {"lazy": False}

    def test_minimal_long_form_applies_defaults(self):
        spec = ValidatorSpec.from_config("companies", {"class": "my_pkg.Schema"})

        assert spec.class_path == "my_pkg.Schema"
        assert spec.on == ("load", "save")
        assert spec.severity == "error"
        assert spec.enabled is True
        assert spec.skip_load_after_save is False
        assert spec.options == {}

    def test_on_accepts_single_string(self):
        spec = ValidatorSpec.from_config(
            "companies", {"class": "my_pkg.Schema", "on": "load"}
        )
        assert spec.on == ("load",)

    def test_options_copied_not_aliased(self):
        options = {"lazy": False}
        spec = ValidatorSpec.from_config(
            "companies", {"class": "my_pkg.Schema", "options": options}
        )
        options["lazy"] = True
        assert spec.options == {"lazy": False}


class TestFromConfigErrors:
    def test_unknown_key_rejected_and_allowed_keys_listed(self):
        with pytest.raises(ValidationConfigurationError, match="companies") as exc_info:
            ValidatorSpec.from_config(
                "companies", {"class": "my_pkg.Schema", "bogus_key": 1}
            )
        message = str(exc_info.value)
        assert "bogus_key" in message
        for allowed in (
            "class",
            "on",
            "severity",
            "enabled",
            "skip_load_after_save",
            "options",
        ):
            assert allowed in message

    def test_missing_class_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="class"):
            ValidatorSpec.from_config("companies", {"on": ["load"]})

    def test_empty_class_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="class"):
            ValidatorSpec.from_config("companies", {"class": ""})

    @pytest.mark.parametrize("bad_on", [["delete"], ["load", "delete"], "delete"])
    def test_bad_on_mode_rejected(self, bad_on):
        with pytest.raises(ValidationConfigurationError, match="'on'"):
            ValidatorSpec.from_config(
                "companies", {"class": "my_pkg.Schema", "on": bad_on}
            )

    def test_empty_on_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="non-empty"):
            ValidatorSpec.from_config("companies", {"class": "my_pkg.Schema", "on": []})

    def test_list_form_reserved(self):
        with pytest.raises(
            ValidationConfigurationError, match="list form is reserved for future use"
        ):
            ValidatorSpec.from_config("companies", ["my_pkg.Schema"])

    @pytest.mark.parametrize("bad_severity", ["strict", "ERROR", "", None, 1])
    def test_bad_severity_rejected(self, bad_severity):
        with pytest.raises(ValidationConfigurationError, match="severity"):
            ValidatorSpec.from_config(
                "companies", {"class": "my_pkg.Schema", "severity": bad_severity}
            )

    @pytest.mark.parametrize("bad_config", [1, 1.5, True, None])
    def test_non_str_non_dict_rejected(self, bad_config):
        with pytest.raises(ValidationConfigurationError, match="companies"):
            ValidatorSpec.from_config("companies", bad_config)

    def test_non_dict_options_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="options"):
            ValidatorSpec.from_config(
                "companies", {"class": "my_pkg.Schema", "options": [1, 2]}
            )


class TestToConfigRoundTrip:
    def test_shorthand_round_trips_to_string(self):
        spec = ValidatorSpec.from_config("companies", "my_pkg.Schema")
        assert spec.to_config() == "my_pkg.Schema"

    def test_default_long_form_collapses_to_string(self):
        spec = ValidatorSpec.from_config("companies", {"class": "my_pkg.Schema"})
        assert spec.to_config() == "my_pkg.Schema"

    def test_long_form_round_trips_to_dict_with_non_defaults_only(self):
        config = {
            "class": "my_pkg.Schema",
            "on": ["save"],
            "severity": "warn",
            "enabled": False,
            "skip_load_after_save": True,
            "options": {"lazy": False},
        }
        spec = ValidatorSpec.from_config("companies", config)
        assert spec.to_config() == config

    def test_partial_long_form_omits_default_fields(self):
        spec = ValidatorSpec.from_config(
            "companies", {"class": "my_pkg.Schema", "severity": "warn"}
        )
        assert spec.to_config() == {"class": "my_pkg.Schema", "severity": "warn"}

    @pytest.mark.parametrize(
        "config",
        [
            "my_pkg.Schema",
            {"class": "my_pkg.Schema", "on": ["load"]},
            {"class": "my_pkg.Schema", "skip_load_after_save": True},
            {
                "class": "my_pkg.Schema",
                "on": ["save"],
                "severity": "warn",
                "enabled": False,
                "options": {"head": 100},
            },
        ],
    )
    def test_from_config_to_config_round_trip_is_stable(self, config):
        spec = ValidatorSpec.from_config("companies", config)
        respec = ValidatorSpec.from_config("companies", spec.to_config())
        assert respec == spec


class TestYaml11OnKeyNormalisation:
    """YAML 1.1 parses an unquoted ``on`` key as boolean True (the "Norway
    problem"); ``from_config`` must normalise it back."""

    def test_boolean_true_key_is_treated_as_on(self):
        # what yaml.safe_load / OmegaConfigLoader deliver for `on: [save]`
        spec = ValidatorSpec.from_config(
            "companies", {"class": "my_pkg.Schema", True: ["save"]}
        )
        assert spec.on == ("save",)

    def test_boolean_true_key_round_trips_through_real_yaml(self):
        import yaml

        raw = yaml.safe_load("{class: my_pkg.Schema, on: [load, save]}")
        assert True in raw  # precondition: the footgun is real
        spec = ValidatorSpec.from_config("companies", raw)
        assert spec.on == ("load", "save")
