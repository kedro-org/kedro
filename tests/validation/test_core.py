"""Tests for `kedro.validation.core`: `ValidatorSpec` parsing and
serialisation, validator resolution and the preflight check."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

from kedro.validation import (
    CallableValidator,
    PanderaValidator,
    ValidationConfigurationError,
    Validator,
    ValidatorSpec,
    preflight_check,
    resolve_validator,
)

_MODULE = "tests.validation.test_core"


# --- Module-level objects importable by class path -------------------------


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(unique=True)
    company_rating: float = pa.Field(ge=0)

    class Config:
        strict = False


COMPANIES_SCHEMA_INSTANCE = pa.DataFrameSchema(
    {"id": pa.Column(int), "company_rating": pa.Column(float, pa.Check.ge(0))}
)


class ThresholdValidator:
    """Custom validator class taking constructor options.

    This is the runtime_checkable footgun target: it defines `validate` so
    `isinstance(cls, Validator)` would be True for the CLASS itself, but
    resolution must instantiate it (with options) rather than return the
    uninstantiated class.
    """

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def validate(self, data):
        if (data["company_rating"] < self.threshold).any():
            raise ValueError(f"ratings below {self.threshold}")
        return data


class NoValidateMethod:
    """Instantiable class that does not satisfy the Validator protocol."""

    def __init__(self):
        pass


INSTANCE_VALIDATOR = ThresholdValidator(threshold=1.0)


def assert_non_empty(data):
    """Plain assertion-style validator function (returns None)."""
    assert len(data) > 0, "data is empty"


def double_ratings(data):
    """Plain transforming validator function (returns data)."""
    data = data.copy()
    data["company_rating"] = data["company_rating"] * 2
    return data


NOT_A_VALIDATOR = 42


class RejectingValidator:
    """Validator whose constructor validates its own arguments."""

    def __init__(self, threshold: float = 0.0):
        raise ValueError(f"threshold {threshold} rejected")

    def validate(self, data):
        return data


class NonCallableValidate:
    """`validate` exists but is not callable."""

    validate = None


class NotItsOwnInstance:
    """Defines `validate` on the class but constructs something else."""

    def __new__(cls):
        return 42

    def validate(self, data):
        return data


# --- Tests ------------------------------------------------------------------


class TestPanderaResolution:
    def test_dataframe_model_class_routes_through_adapter(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema")
        validator = resolve_validator(spec)

        assert isinstance(validator, PanderaValidator)
        assert "CompaniesSchema" in repr(validator)

    def test_dataframe_model_with_options(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.CompaniesSchema",
            options={"lazy": False, "head": 10},
        )
        validator = resolve_validator(spec)

        assert isinstance(validator, PanderaValidator)
        assert validator._lazy is False
        assert validator._head == 10

    def test_dataframe_schema_instance_accepted(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.COMPANIES_SCHEMA_INSTANCE")
        validator = resolve_validator(spec)

        assert isinstance(validator, PanderaValidator)
        assert "DataFrameSchema" in repr(validator)

    def test_resolved_pandera_validator_validates(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema")
        validator = resolve_validator(spec)
        df = pd.DataFrame({"id": [1, 2], "company_rating": [0.5, 1.0]})

        result = validator.validate(df)

        pd.testing.assert_frame_equal(result, df)

    def test_unsupported_pandera_option_is_config_error(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.CompaniesSchema", options={"bogus_option": 1}
        )
        with pytest.raises(
            ValidationConfigurationError, match="CompaniesSchema"
        ) as exc_info:
            resolve_validator(spec)
        message = str(exc_info.value)
        assert "bogus_option" in message
        assert "lazy, head, tail, sample, random_state" in message


class TestCustomClassResolution:
    def test_class_with_options_is_instantiated(self):
        """The runtime_checkable footgun: must NOT return the class itself."""
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.ThresholdValidator", options={"threshold": 2.5}
        )
        validator = resolve_validator(spec)

        assert isinstance(validator, ThresholdValidator)
        assert validator.threshold == 2.5

    def test_class_without_options_is_instantiated_with_defaults(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.ThresholdValidator")
        validator = resolve_validator(spec)

        assert isinstance(validator, ThresholdValidator)
        assert validator.threshold == 0.0

    def test_bad_constructor_option_is_config_error_naming_option(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.ThresholdValidator", options={"bogus": 1}
        )
        with pytest.raises(ValidationConfigurationError) as exc_info:
            resolve_validator(spec)
        message = str(exc_info.value)
        assert f"{_MODULE}.ThresholdValidator" in message
        assert "bogus" in message

    def test_class_without_validate_method_rejected_before_construction(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NoValidateMethod")
        with pytest.raises(ValidationConfigurationError, match="validate"):
            resolve_validator(spec)

    def test_non_callable_validate_attribute_rejected(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NonCallableValidate")
        with pytest.raises(ValidationConfigurationError, match="validate"):
            resolve_validator(spec)

    def test_constructor_error_of_any_type_is_config_error(self):
        # constructors may validate their own arguments with any exception
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.RejectingValidator", options={"threshold": -1}
        )
        with pytest.raises(ValidationConfigurationError) as exc_info:
            resolve_validator(spec)
        assert f"{_MODULE}.RejectingValidator" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_class_constructing_a_non_validator_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NotItsOwnInstance")
        with pytest.raises(ValidationConfigurationError, match="validate"):
            resolve_validator(spec)


class TestInstanceResolution:
    def test_module_level_instance_accepted(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.INSTANCE_VALIDATOR")
        validator = resolve_validator(spec)

        assert validator is INSTANCE_VALIDATOR

    def test_instance_with_options_is_config_error(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.INSTANCE_VALIDATOR", options={"threshold": 5.0}
        )
        with pytest.raises(ValidationConfigurationError, match="instance"):
            resolve_validator(spec)


class TestCallableResolution:
    def test_plain_function_wrapped_in_callable_validator(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        validator = resolve_validator(spec)

        assert isinstance(validator, CallableValidator)

    def test_assertion_style_function_returns_original_data(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        validator = resolve_validator(spec)
        df = pd.DataFrame({"id": [1]})

        assert validator.validate(df) is df

    def test_assertion_style_function_raise_propagates(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        validator = resolve_validator(spec)

        with pytest.raises(AssertionError, match="data is empty"):
            validator.validate(pd.DataFrame())

    def test_transforming_function_returns_transformed_data(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.double_ratings")
        validator = resolve_validator(spec)
        df = pd.DataFrame({"company_rating": [1.0, 2.0]})

        result = validator.validate(df)

        assert result["company_rating"].tolist() == [2.0, 4.0]

    def test_function_with_options_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty", options={"x": 1})
        with pytest.raises(ValidationConfigurationError, match="callable") as exc_info:
            resolve_validator(spec)
        assert "drop the options" in str(exc_info.value)

    def test_callable_validator_repr_names_the_function(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        assert "assert_non_empty" in repr(resolve_validator(spec))


class TestValidatorProtocolConformance:
    """Everything `resolve_validator` returns satisfies the `Validator`
    protocol, whatever shape the declaration took."""

    @pytest.mark.parametrize(
        "class_path,options",
        [
            (f"{_MODULE}.CompaniesSchema", {}),
            (f"{_MODULE}.ThresholdValidator", {"threshold": 1.0}),
            (f"{_MODULE}.INSTANCE_VALIDATOR", {}),
            (f"{_MODULE}.assert_non_empty", {}),
        ],
        ids=["pandera-model", "custom-class", "instance", "callable"],
    )
    def test_resolved_validator_satisfies_protocol(self, class_path, options):
        spec = ValidatorSpec(class_path=class_path, options=options)
        assert isinstance(resolve_validator(spec), Validator)


class TestImportErrors:
    def test_missing_module_is_config_error_with_hint(self):
        spec = ValidatorSpec(class_path="definitely_not_installed_pkg.Schema")
        with pytest.raises(ValidationConfigurationError) as exc_info:
            resolve_validator(spec)
        message = str(exc_info.value)
        assert "definitely_not_installed_pkg.Schema" in message
        assert "Check that the class path is correct" in message
        assert isinstance(exc_info.value.__cause__, ModuleNotFoundError)

    def test_missing_pandera_submodule_hints_class_path(self):
        spec = ValidatorSpec(class_path="pandera.no_such_submodule.Schema")
        with pytest.raises(
            ValidationConfigurationError,
            match="pandera is installed but .* check the class path",
        ):
            resolve_validator(spec)

    def test_import_hint_when_pandera_missing_entirely(self, monkeypatch):
        import importlib.util

        from kedro.validation.core import _import_error_hint

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        assert "pip install 'kedro[pandera-pandas]'" in _import_error_hint("pandera")
        assert "pip install 'kedro[pandera-pandas]'" in _import_error_hint(
            "pandera.pandas"
        )

    def test_import_hint_generic_for_unknown_names(self):
        from kedro.validation.core import _import_error_hint

        assert "Check that the class path" in _import_error_hint("")
        assert "Check that the class path" in _import_error_hint("some_pkg")

    def test_missing_attribute_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NoSuchAttribute")
        with pytest.raises(ValidationConfigurationError, match="NoSuchAttribute"):
            resolve_validator(spec)

    def test_dotless_class_path_is_config_error(self):
        spec = ValidatorSpec(class_path="NoModuleJustAName")
        with pytest.raises(ValidationConfigurationError, match="NoModuleJustAName"):
            resolve_validator(spec)

    def test_non_validator_object_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NOT_A_VALIDATOR")
        with pytest.raises(
            ValidationConfigurationError, match="not a validator"
        ) as exc_info:
            resolve_validator(spec)
        assert "int" in str(exc_info.value)


class TestPreflightCheck:
    def test_missing_package_produces_warning(self):
        specs = {
            "companies": ValidatorSpec(class_path="definitely_not_installed_pkg.Schema")
        }
        warnings = preflight_check(specs)

        assert len(warnings) == 1
        assert "companies" in warnings[0]
        assert "definitely_not_installed_pkg" in warnings[0]

    def test_installed_packages_produce_no_warnings(self):
        specs = {
            "companies": ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema"),
            "shuttles": ValidatorSpec(class_path="pandera.pandas.DataFrameModel"),
        }
        assert preflight_check(specs) == []

    def test_empty_specs_produce_no_warnings(self):
        assert preflight_check({}) == []


class TestPreflightEdgeCases:
    def test_find_spec_raising_counts_as_missing(self, monkeypatch):
        import importlib.util

        def boom(name):
            raise ImportError("boom")

        monkeypatch.setattr(importlib.util, "find_spec", boom)
        specs = {"ds": ValidatorSpec(class_path="weird_pkg.Schema")}
        warnings = preflight_check(specs)
        assert len(warnings) == 1

    def test_invalid_class_path_gets_clear_warning(self):
        specs = {"ds": ValidatorSpec(class_path=".weird.Schema")}
        warnings = preflight_check(specs)
        assert len(warnings) == 1
        assert "invalid class path" in warnings[0]

    def test_missing_pandera_mentions_backend_extras(self, monkeypatch):
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda name: None)
        specs = {"ds": ValidatorSpec(class_path="pandera.pandas.Schema")}
        warnings = preflight_check(specs)
        assert "kedro[pandera-pandas]" in warnings[0]
        assert "pandera-polars" in warnings[0]


def test_string_shorthand_applies_defaults():
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

    def test_on_is_canonicalised(self):
        # duplicates collapse and the order is normalised to (load, save)
        spec = ValidatorSpec.from_dataset_config(
            "companies", {"class": "my_pkg.Schema", "on": ["save", "load", "load"]}
        )
        assert spec.on == ("load", "save")
        assert spec.to_config() == "my_pkg.Schema"  # defaults collapse

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
