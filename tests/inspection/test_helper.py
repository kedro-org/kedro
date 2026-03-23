"""Tests for helper utilities in kedro/inspection/helper.py."""

from __future__ import annotations

from kedro.config import MissingConfigException
from kedro.inspection.helper import (
    _get_parameter_keys,
    _make_config_loader,
    _resolve_factory_patterns,
)
from kedro.inspection.models import DatasetSnapshot, NodeSnapshot, PipelineSnapshot


def _make_node_snapshot(inputs: list[str], outputs: list[str]) -> NodeSnapshot:
    return NodeSnapshot(name="n", inputs=inputs, outputs=outputs)


def _make_pipeline_snapshot(nodes: list[NodeSnapshot]) -> PipelineSnapshot:
    return PipelineSnapshot(name="p", nodes=nodes)


class TestMakeConfigLoader:
    def test_uses_settings_class_and_args(self, mocker, tmp_path):
        """_make_config_loader instantiates CONFIG_LOADER_CLASS with the right args."""
        mock_loader_class = mocker.MagicMock()
        mocker.patch(
            "kedro.inspection.helper.settings",
            mocker.MagicMock(
                CONFIG_LOADER_CLASS=mock_loader_class,
                CONFIG_LOADER_ARGS={"base_env": "base", "default_run_env": "local"},
                CONF_SOURCE="conf",
            ),
        )

        _make_config_loader(tmp_path, env="staging")

        mock_loader_class.assert_called_once_with(
            conf_source=str(tmp_path / "conf"),
            env="staging",
            base_env="base",
            default_run_env="local",
        )

    def test_conf_source_uses_project_path(self, mocker, tmp_path):
        """conf_source is derived from project_path / CONF_SOURCE."""
        mock_loader_class = mocker.MagicMock()
        mocker.patch(
            "kedro.inspection.helper.settings",
            mocker.MagicMock(
                CONFIG_LOADER_CLASS=mock_loader_class,
                CONFIG_LOADER_ARGS={},
                CONF_SOURCE="my_conf",
            ),
        )

        _make_config_loader(tmp_path)

        _, kwargs = mock_loader_class.call_args
        assert kwargs["conf_source"] == str(tmp_path / "my_conf")

    def test_returns_loader_instance(self, mocker, tmp_path):
        """Return value is whatever the loader class returns."""
        sentinel = object()
        mock_loader_class = mocker.MagicMock(return_value=sentinel)
        mocker.patch(
            "kedro.inspection.helper.settings",
            mocker.MagicMock(
                CONFIG_LOADER_CLASS=mock_loader_class,
                CONFIG_LOADER_ARGS={},
                CONF_SOURCE="conf",
            ),
        )

        result = _make_config_loader(tmp_path)
        assert result is sentinel


class TestGetParameterKeys:
    def test_returns_sorted_keys(self, mocker):
        config_loader = mocker.MagicMock()
        config_loader.__getitem__.return_value = {
            "z_param": 1,
            "a_param": 2,
            "m_param": 3,
        }
        result = _get_parameter_keys(config_loader)
        assert result == ["a_param", "m_param", "z_param"]

    def test_empty_on_key_error(self, mocker):
        config_loader = mocker.MagicMock()
        config_loader.__getitem__.side_effect = KeyError("parameters")
        assert _get_parameter_keys(config_loader) == []

    def test_empty_on_missing_config(self, mocker):
        config_loader = mocker.MagicMock()
        config_loader.__getitem__.side_effect = MissingConfigException("parameters")
        assert _get_parameter_keys(config_loader) == []

    def test_empty_params(self, mocker):
        config_loader = mocker.MagicMock()
        config_loader.__getitem__.return_value = {}
        assert _get_parameter_keys(config_loader) == []

    def test_nested_params_returns_top_level_keys(self, mocker):
        """Only top-level keys are returned, not nested ones."""
        config_loader = mocker.MagicMock()
        config_loader.__getitem__.return_value = {
            "model": {"learning_rate": 0.01},
            "batch_size": 32,
        }
        result = _get_parameter_keys(config_loader)
        assert result == ["batch_size", "model"]


class TestResolveFactoryPatterns:
    def test_no_patterns_returns_unchanged(self):
        """If no factory patterns exist, datasets dict is returned as-is."""
        datasets = {
            "companies": DatasetSnapshot(name="companies", type="pandas.CSVDataset"),
        }
        pipelines = [
            _make_pipeline_snapshot([_make_node_snapshot(["companies"], ["output"])])
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert result == datasets

    def test_concrete_pipeline_ds_already_in_datasets_not_duplicated(self):
        """Pipeline datasets that already have direct entries are not replaced."""
        datasets = {
            "companies": DatasetSnapshot(name="companies", type="pandas.CSVDataset"),
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}",
                type="pandas.CSVDataset",
                filepath="data/{name}.csv",
            ),
        }
        pipelines = [
            _make_pipeline_snapshot([_make_node_snapshot(["companies"], ["output"])])
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        # 'companies' direct entry should not be overwritten
        assert result["companies"].type == "pandas.CSVDataset"
        assert result["companies"].filepath is None

    def test_factory_pattern_resolved_for_pipeline_input(self):
        """Pipeline input matching a factory pattern gets a concrete entry."""
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}",
                type="pandas.CSVDataset",
                filepath="data/{name}.csv",
            ),
        }
        pipelines = [
            _make_pipeline_snapshot(
                [_make_node_snapshot(["data_science.companies"], ["output"])]
            )
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert "data_science.companies" in result
        assert result["data_science.companies"].type == "pandas.CSVDataset"
        assert result["data_science.companies"].filepath == "data/companies.csv"

    def test_factory_pattern_resolved_for_pipeline_output(self):
        """Pipeline output matching a factory pattern gets a concrete entry."""
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}",
                type="pandas.CSVDataset",
                filepath="data/{name}.csv",
            ),
        }
        pipelines = [
            _make_pipeline_snapshot(
                [_make_node_snapshot(["raw"], ["data_science.processed"])]
            )
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert "data_science.processed" in result
        assert result["data_science.processed"].filepath == "data/processed.csv"

    def test_original_pattern_entry_preserved(self):
        """The factory pattern entry itself is still present in the result."""
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}", type="pandas.CSVDataset", filepath=None
            ),
        }
        pipelines = [_make_pipeline_snapshot([_make_node_snapshot(["ns.ds"], ["out"])])]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert "{namespace}.{name}" in result

    def test_no_match_dataset_not_added(self):
        """A pipeline dataset that does not match any pattern is not added."""
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}", type="pandas.CSVDataset", filepath=None
            ),
        }
        # "plain_name" has no dots, so won't match "{namespace}.{name}"
        pipelines = [
            _make_pipeline_snapshot([_make_node_snapshot(["plain_name"], ["out"])])
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert "plain_name" not in result

    def test_pattern_without_filepath_gives_none_filepath(self):
        """Resolved entries have None filepath when the pattern has no filepath."""
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}", type="kedro.io.MemoryDataset", filepath=None
            ),
        }
        pipelines = [_make_pipeline_snapshot([_make_node_snapshot(["ns.ds"], ["out"])])]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert result["ns.ds"].filepath is None

    def test_empty_pipelines_returns_unchanged(self):
        """No pipelines means no enrichment needed."""
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}", type="pandas.CSVDataset", filepath=None
            ),
        }
        result = _resolve_factory_patterns(datasets, [])
        assert result == datasets

    def test_filepath_when_placeholder_unresolvable(self):
        """Falls back to the raw filepath when it contains a key absent from the pattern."""
        datasets = {
            "{name}": DatasetSnapshot(
                name="{name}",
                type="pandas.CSVDataset",
                filepath="data/{name}/{unknown}.csv",
            ),
        }
        pipelines = [
            _make_pipeline_snapshot([_make_node_snapshot(["companies"], ["out"])])
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert result["companies"].filepath == "data/{name}/{unknown}.csv"

    def test_more_specific_pattern_wins_regardless_of_catalog_order(self):
        """Pattern with higher specificity is chosen even when defined after a generic one."""
        # Less-specific pattern declared FIRST in the dict (catalog order)
        datasets = {
            "{namespace}.{name}": DatasetSnapshot(
                name="{namespace}.{name}",
                type="pandas.CSVDataset",
                filepath="data/{name}.csv",
            ),
            "{namespace}.int_{name}": DatasetSnapshot(
                name="{namespace}.int_{name}",
                type="pandas.ParquetDataset",
                filepath="data/int_{name}.parquet",
            ),
        }
        pipelines = [
            _make_pipeline_snapshot(
                [_make_node_snapshot(["data_science.int_customers"], ["out"])]
            )
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        # More specific pattern "{namespace}.int_{name}" must win
        assert result["data_science.int_customers"].type == "pandas.ParquetDataset"
        assert (
            result["data_science.int_customers"].filepath
            == "data/int_customers.parquet"
        )

    def test_multiple_nodes_across_pipelines(self):
        """Dataset names from multiple pipelines and nodes are all considered."""
        datasets = {
            "{ns}.{name}": DatasetSnapshot(
                name="{ns}.{name}", type="pandas.CSVDataset", filepath="{name}.csv"
            ),
        }
        pipelines = [
            _make_pipeline_snapshot([_make_node_snapshot(["p1.ds_a"], ["p1.ds_b"])]),
            _make_pipeline_snapshot([_make_node_snapshot(["p2.ds_c"], ["out"])]),
        ]
        result = _resolve_factory_patterns(datasets, pipelines)
        assert "p1.ds_a" in result
        assert "p1.ds_b" in result
        assert "p2.ds_c" in result
