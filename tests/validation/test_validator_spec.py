"""Tests for `ValidatorSpec` parsing and serialisation."""

from __future__ import annotations

import pytest

from kedro.validation import ValidationConfigurationError, ValidatorSpec


class TestFromDatasetConfigShorthand:
    def test_string_shorthand(self):
        spec = ValidatorSpec.from_dataset_config(
            "companies", "my_pkg.schemas.CompaniesSchema"
        )

        assert spec.class_path == "my_pkg.schemas.CompaniesSchema"
        assert spec.on == ("load", "save")
        assert spec.severity == "error"
        assert spec.enabled is True
        assert spec.skip_load_after_save is False
        assert spec.options == {}


class TestFromDatasetConfigLongForm:
    def test_full_long_form(self):
        spec = ValidatorSpec.from_dataset_config(
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
        spec = ValidatorSpec.from_dataset_config(
            "companies", {"class": "my_pkg.Schema"}
        )

        assert spec.class_path == "my_pkg.Schema"
        assert spec.on == ("load", "save")
        assert spec.severity == "error"
        assert spec.enabled is True
        assert spec.skip_load_after_save is False
        assert spec.options == {}

    def test_on_accepts_single_string(self):
        spec = ValidatorSpec.from_dataset_config(
            "companies", {"class": "my_pkg.Schema", "on": "load"}
        )
        assert spec.on == ("load",)

    def test_options_copied_not_aliased(self):
        options = {"lazy": False}
        spec = ValidatorSpec.from_dataset_config(
            "companies", {"class": "my_pkg.Schema", "options": options}
        )
        options["lazy"] = True
        assert spec.options == {"lazy": False}


class TestFromDatasetConfigErrors:
    def test_unknown_key_rejected_and_allowed_keys_listed(self):
        with pytest.raises(ValidationConfigurationError, match="companies") as exc_info:
            ValidatorSpec.from_dataset_config(
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

    def test_unknown_keys_of_mixed_types_are_listed(self):
        # YAML can supply non-string keys: `1:`, or `off:` which reads as the
        # boolean False. They are not orderable against the string keys.
        with pytest.raises(ValidationConfigurationError) as exc_info:
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", 1: "a", False: "b", "z": "c"}
            )
        message = str(exc_info.value)
        assert "unknown key(s)" in message
        assert "'z'" in message and "1" in message

    def test_missing_class_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="class"):
            ValidatorSpec.from_dataset_config("companies", {"on": ["load"]})

    def test_empty_class_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="class"):
            ValidatorSpec.from_dataset_config("companies", {"class": ""})

    @pytest.mark.parametrize("bad_on", [["delete"], ["load", "delete"], "delete"])
    def test_bad_on_mode_rejected(self, bad_on):
        with pytest.raises(ValidationConfigurationError, match="'on'"):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", "on": bad_on}
            )

    def test_empty_on_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="non-empty"):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", "on": []}
            )

    def test_list_form_reserved(self):
        with pytest.raises(
            ValidationConfigurationError, match="list form is reserved for future use"
        ):
            ValidatorSpec.from_dataset_config("companies", ["my_pkg.Schema"])

    @pytest.mark.parametrize("bad_severity", ["strict", "ERROR", "", None, 1])
    def test_bad_severity_rejected(self, bad_severity):
        with pytest.raises(ValidationConfigurationError, match="severity"):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", "severity": bad_severity}
            )

    @pytest.mark.parametrize("bad_config", [1, 1.5, True, None])
    def test_non_str_non_dict_rejected(self, bad_config):
        with pytest.raises(ValidationConfigurationError, match="companies"):
            ValidatorSpec.from_dataset_config("companies", bad_config)

    def test_non_dict_options_rejected(self):
        with pytest.raises(ValidationConfigurationError, match="options"):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", "options": [1, 2]}
            )


class TestToConfigRoundTrip:
    def test_shorthand_round_trips_to_string(self):
        spec = ValidatorSpec.from_dataset_config("companies", "my_pkg.Schema")
        assert spec.to_config() == "my_pkg.Schema"

    def test_default_long_form_collapses_to_string(self):
        spec = ValidatorSpec.from_dataset_config(
            "companies", {"class": "my_pkg.Schema"}
        )
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
        spec = ValidatorSpec.from_dataset_config("companies", config)
        assert spec.to_config() == config

    def test_partial_long_form_omits_default_fields(self):
        spec = ValidatorSpec.from_dataset_config(
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
    def test_from_dataset_config_to_config_round_trip_is_stable(self, config):
        spec = ValidatorSpec.from_dataset_config("companies", config)
        respec = ValidatorSpec.from_dataset_config("companies", spec.to_config())
        assert respec == spec


class TestYaml11OnKeyNormalisation:
    """YAML 1.1 parses an unquoted `on` key as boolean True (the "Norway
    problem"); `from_dataset_config` must normalise it back."""

    def test_boolean_true_key_is_treated_as_on(self):
        # what yaml.safe_load / OmegaConfigLoader deliver for `on: [save]`
        spec = ValidatorSpec.from_dataset_config(
            "companies", {"class": "my_pkg.Schema", True: ["save"]}
        )
        assert spec.on == ("save",)

    def test_boolean_true_key_round_trips_through_real_yaml(self):
        import yaml

        raw = yaml.safe_load("{class: my_pkg.Schema, on: [load, save]}")
        assert True in raw  # precondition: the footgun is real
        spec = ValidatorSpec.from_dataset_config("companies", raw)
        assert spec.on == ("load", "save")

    def test_quoted_and_unquoted_on_keys_together_are_config_error(self):
        # Only one of the two keys can survive normalisation.
        with pytest.raises(ValidationConfigurationError, match="single 'on' key"):
            ValidatorSpec.from_dataset_config(
                "companies",
                {"class": "my_pkg.Schema", True: ["load"], "on": ["save"]},
            )

    def test_on_key_collision_from_real_yaml_is_config_error(self):
        import yaml

        raw = yaml.safe_load('{class: my_pkg.Schema, on: [load], "on": [save]}')
        assert True in raw and "on" in raw  # precondition: both keys survive
        with pytest.raises(ValidationConfigurationError, match="single 'on' key"):
            ValidatorSpec.from_dataset_config("companies", raw)

    def test_integer_key_is_not_mistaken_for_the_on_key(self):
        # `True == 1` and `hash(True) == hash(1)`, so an integer key must not
        # be renamed to `on`.
        with pytest.raises(ValidationConfigurationError, match=r"unknown key\(s\)"):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", 1: ["load"]}
            )


class TestStrictTypes:
    def test_on_of_invalid_type_is_config_error(self):
        with pytest.raises(ValidationConfigurationError, match="'on' must be"):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", "on": 42}
            )

    @pytest.mark.parametrize("flag", ["enabled", "skip_load_after_save"])
    def test_non_boolean_flag_is_config_error(self, flag):
        with pytest.raises(
            ValidationConfigurationError, match=f"'{flag}' must be a boolean"
        ):
            ValidatorSpec.from_dataset_config(
                "companies", {"class": "my_pkg.Schema", flag: "false"}
            )
