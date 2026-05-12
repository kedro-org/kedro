import logging

import pytest

from kedro.io import CatalogConfigResolver
from kedro.io.core import DatasetError


# Helper method
def run_validation(ds_name, ds_config):
    try:
        CatalogConfigResolver._validate_pattern_config(ds_name, ds_config)
    except DatasetError as exc:
        return exc
    return None


class TestCatalogConfigResolver:
    def test_unresolve_credentials(self, correct_config):
        """Test unresolve dataset credentials to original format."""
        config = correct_config["catalog"]
        credentials = correct_config["credentials"]
        resolved_configs = CatalogConfigResolver._resolve_credentials(
            config, credentials
        )

        unresolved_config, unresolved_credentials = (
            CatalogConfigResolver._unresolve_credentials(
                cred_name="s3", ds_config=resolved_configs
            )
        )
        assert config == unresolved_config
        assert credentials == unresolved_credentials

    def test_unresolve_credentials_two_keys(self, correct_config):
        """Test unresolve dataset credentials to original format when two credentials keys provided."""
        config = correct_config["catalog"]
        credentials = correct_config["credentials"]

        resolved_configs = CatalogConfigResolver._resolve_credentials(
            config, credentials
        )
        resolved_configs["cars"]["metadata"] = {"credentials": {}}

        unresolved_config, unresolved_credentials = (
            CatalogConfigResolver._unresolve_credentials(
                cred_name="s3", ds_config=resolved_configs
            )
        )
        unresolved_config["cars"].pop("metadata")
        assert config == unresolved_config
        assert credentials == unresolved_credentials

    def test_sort_patterns(self):
        dataset_patterns = {
            "{name}": "dataset4",  # catch-all pattern
            "path/{dataset}/file": "dataset2",
            "path/to/{dataset}/data": "dataset1",
            "data/{dataset}": "dataset3",
        }

        sorted_patterns = CatalogConfigResolver._sort_patterns(dataset_patterns)

        # Assert that the patterns are sorted according to the logic
        sorted_dataset_values = list(sorted_patterns.values())

        # Check that they are sorted by specificity, then number of placeholders, then alphabetically
        assert sorted_dataset_values == ["dataset1", "dataset2", "dataset3", "dataset4"]

    def test_multiple_catch_all_patterns(self):
        dataset_patterns = {
            "{name}": "dataset1",  # catch-all pattern
            "path/{dataset}/file": "dataset2",
            "{value}": "dataset3",  # catch-all pattern (second one)
        }

        # Ensure the exception is raised for multiple catch-all patterns
        with pytest.raises(
            DatasetError, match="Multiple catch-all patterns found in the catalog"
        ):
            CatalogConfigResolver._sort_patterns(dataset_patterns)

    @pytest.mark.parametrize(
        "ds_name, ds_config, expected_error",
        [
            # Valid cases
            ("{name}#csv", {"path": "path/to/{name}#csv/data"}, None),
            (
                "{name}#csv",
                ["path/to/{name}#csv/data", "path/to/{name}#excel/data"],
                None,
            ),
            (
                "{name}#csv",
                ("path/to/{name}#pq/data", "path/to/{name}#excel/data"),
                None,
            ),
            ("{name}#csv{tangent}", "path/to/{name}#pq/data", None),
            # Invalid cases
            (
                "{name}#csv{tangent}",
                {"path": "path/to/{dataset}/data", "metadata": "{user}"},
                DatasetError,
            ),
            (
                "{dataset}#excel",
                ["path/to/{dataset}/data", "path/to/{dataset}/{user}/data"],
                DatasetError,
            ),
            (
                "{dataset}#pq",
                ("path/to/{dataset}/data", "path/to/{dataset}/{user}/data"),
                DatasetError,
            ),
            ("{user}", "path/to/{dataset}/{user}/data", DatasetError),
        ],
    )
    def test_validate_pattern_config(self, ds_name, ds_config, expected_error):
        error = run_validation(ds_name, ds_config)

        if expected_error:
            assert isinstance(
                error, expected_error
            ), f"Expected {expected_error}, got {type(error)}"
        else:
            assert error is None, f"Unexpected error: {error}"

    # Parametrizing edge cases
    @pytest.mark.parametrize(
        "ds_name, ds_config, expected_error",
        [
            ("{dataset}#csv", {}, None),  # Empty config
            (
                "{dataset}#excel",
                {"path": "path/to/data"},
                None,
            ),  # No placeholders in config
            (
                "{dataset}.{some}",
                {"path": "path/to/{dataset}/{user}/data"},
                DatasetError,
            ),  # Extra placeholders
        ],
    )
    def test_validate_pattern_config_edge_cases(
        self, ds_name, ds_config, expected_error
    ):
        error = run_validation(ds_name, ds_config)

        if expected_error:
            assert isinstance(
                error, expected_error
            ), f"Expected {expected_error}, got {type(error)}"
        else:
            assert error is None, f"Unexpected error: {error}"

    @pytest.mark.parametrize(
        "ds_name, pattern, config, expected_config",
        [
            # Valid cases where placeholders in the pattern should be replaced
            (
                "my_dataset#csv",
                "{dataset_name}#csv",
                {"path": "path/to/{dataset_name}#csv/data"},
                {"path": "path/to/my_dataset#csv/data"},
            ),  # placeholder {dataset} replaced with 'my_dataset'
            # Config as list of strings
            (
                "my_dataset#csv",
                "{dataset_name}#csv",
                ["path/to/{dataset_name}/data", "another/path/to/{dataset_name}/data"],
                ["path/to/my_dataset/data", "another/path/to/my_dataset/data"],
            ),  # both replaced
            # Config as tuple
            (
                "my_dataset#csv",
                "{dataset_name}#csv",
                ("path/to/{dataset_name}/data", "another/path/to/{dataset_name}/data"),
                ["path/to/my_dataset/data", "another/path/to/my_dataset/data"],
            ),  # both replaced
            # Config as string
            (
                "my_dataset#csv",
                "{dataset_name}#csv",
                "path/to/{dataset_name}/data",
                "path/to/my_dataset/data",
            ),  # string pattern replaced
            # Nested dictionary (testing recursion for dicts)
            (
                "my_dataset#csv",
                "{dataset_name}#csv",
                {"path": {"subpath": "path/to/{dataset_name}/data"}},
                {"path": {"subpath": "path/to/my_dataset/data"}},
            ),  # nested string replaced
        ],
    )
    def test_resolve_dataset_config(self, ds_name, pattern, config, expected_config):
        result = CatalogConfigResolver._resolve_dataset_config(ds_name, pattern, config)
        assert result == expected_config

    def test_init_warning_for_no_default_runtime_pattern(self, caplog):
        """Test warning is logged when default_runtime_pattern is None"""
        with caplog.at_level(logging.WARNING):
            CatalogConfigResolver(
                config={}, credentials={}, default_runtime_patterns=None
            )
            assert "Since runtime patterns are not provided" in caplog.text

    def test_resolve_dataset_config_preserves_tuple_subclass(self):
        """Tuple subclasses (e.g. sqlalchemy.engine.URL) should not be
        iterated over during pattern resolution."""
        from collections import namedtuple

        # Simulate sqlalchemy.engine.URL which is a named tuple
        FakeURL = namedtuple(
            "FakeURL",
            ["drivername", "username", "password", "host", "port", "database"],
        )
        url = FakeURL("postgresql", "user", "pass", "localhost", 5432, "mydb")
        config = {"con": url, "table_name": "{name}"}
        result = CatalogConfigResolver._resolve_dataset_config(
            "ns.my_table", "{namespace}.{name}", config
        )
        # The URL object should pass through unchanged
        assert result["con"] is url
        assert result["table_name"] == "my_table"

    def test_retrieve_already_resolved_config(self):
        """Test retrieving already resolved config."""
        config = {
            "cars": {
                "type": "pandas.CSVDataset",
                "filepath": "s3://example_dataset.csv",
                "credentials": "db_credentials",
            }
        }
        credentials = {"db_credentials": {"user": "username", "pass": "pass"}}
        resolver = CatalogConfigResolver(config, credentials)
        assert "cars" in resolver._resolved_configs
        assert (
            resolver.resolve_pattern(ds_name="cars")
            == resolver._resolved_configs["cars"]
        )
