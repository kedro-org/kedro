"""Tests for `validate_deployment_grouping` and its result model."""

from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any

import pytest

from kedro import inspection
from kedro.inspection import (
    DeploymentGroupingError,
    DeploymentGroupingResult,
    validate_deployment_grouping,
)
from kedro.io import AbstractDataset, CachedDataset, DataCatalog, MemoryDataset
from kedro.io.core import get_protocol_and_path
from kedro.io.data_catalog import SharedMemoryDataCatalog
from kedro.pipeline import GroupedNodes, Pipeline, node, pipeline

PERSISTED = {"type": "pandas.ParquetDataset", "filepath": "s3://bucket/table.parquet"}


def _identity(x):
    return x


def _combine(*args):
    return args[0]


class _FileDataset(AbstractDataset):
    """Dataset object exposing the protocol and path attributes fsspec datasets set."""

    def __init__(self, filepath: str):
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = PurePosixPath(path)

    def load(self) -> Any:  # pragma: no cover
        return None

    def save(self, data: Any) -> None:  # pragma: no cover
        return None

    def _describe(self) -> dict[str, Any]:  # pragma: no cover
        return {}


class _PathDataset(_FileDataset):
    """Dataset object that stores its location under `_path`, like `PartitionedDataset`."""

    def __init__(self, path: str):
        protocol, location = get_protocol_and_path(path)
        self._protocol = protocol
        self._path = location


class _MinimalCatalog:
    """Catalog implementing only lookup, without a config resolver."""

    def __init__(self, datasets: dict[str, Any]):
        self._store = datasets

    def __contains__(self, name: str) -> bool:
        return name in self._store

    def __getitem__(self, name: str) -> Any:
        return self._store[name]


@pytest.fixture
def spaceflights():
    data_processing = pipeline(
        [
            node(
                _identity,
                "companies",
                "preprocessed_companies",
                name="preprocess_companies",
            ),
            node(
                _identity,
                "shuttles",
                "preprocessed_shuttles",
                name="preprocess_shuttles",
            ),
            node(
                _combine,
                ["preprocessed_companies", "preprocessed_shuttles"],
                "model_input_table",
                name="create_model_input_table",
            ),
        ],
        namespace="data_processing",
        inputs={"companies", "shuttles"},
        outputs={"model_input_table"},
    )
    data_science = pipeline(
        [
            node(
                _combine,
                ["model_input_table", "params:model_options"],
                "model",
                name="train_model",
            ),
            node(_identity, "model", "metrics", name="evaluate_model"),
        ],
        namespace="data_science",
        inputs={"model_input_table"},
        parameters={"params:model_options"},
    )
    return data_processing + data_science


@pytest.fixture
def two_groups():
    """Group `a` produces `table`, group `b` reads it. Each group has two nodes."""
    return Pipeline(
        [
            node(_identity, "raw", "prepared", name="prepare", namespace="a"),
            node(_identity, "prepared", "table", name="make", namespace="a"),
            node(_identity, "table", "scored", name="use", namespace="b"),
            node(_identity, "scored", "out", name="report", namespace="b"),
        ]
    )


TWO_GROUPS_NODES = ["a.prepare", "a.make", "b.use", "b.report"]


def _issue_codes(result: DeploymentGroupingResult) -> list[str]:
    return [issue.code for issue in result.issues]


def _problems(result: DeploymentGroupingResult) -> list[str]:
    """Codes of the errors and warnings in `result`, ignoring info."""
    return [issue.code for issue in (*result.errors, *result.warnings)]


class TestBoundaryDatasets:
    def test_persisted_boundary_passes(self, spaceflights):
        catalog = DataCatalog.from_config({"model_input_table": PERSISTED})

        result = validate_deployment_grouping(spaceflights, catalog)

        assert result
        assert result.status == "passed"
        assert result.groups == ("data_processing", "data_science")
        assert result.issues == ()

    def test_in_memory_boundary_is_an_error(self, spaceflights):
        result = validate_deployment_grouping(spaceflights, DataCatalog())

        assert not result
        assert result.status == "failed"
        (issue,) = result.errors
        assert issue.code == "ephemeral_boundary"
        assert issue.datasets == ("model_input_table",)
        assert issue.groups == ("data_processing", "data_science")
        assert "only kept in memory" in issue.message
        assert "group 'data_science'" in issue.message

    def test_free_inputs_and_parameters_are_not_boundaries(self, spaceflights):
        catalog = DataCatalog.from_config({"model_input_table": PERSISTED})

        result = validate_deployment_grouping(spaceflights, catalog)

        reported = {name for issue in result.issues for name in issue.datasets}
        assert reported.isdisjoint({"companies", "shuttles", "params:model_options"})

    def test_datasets_used_within_one_group_are_not_boundaries(self, spaceflights):
        catalog = DataCatalog.from_config({"model_input_table": PERSISTED})

        result = validate_deployment_grouping(spaceflights, catalog)

        assert "data_processing.preprocessed_companies" not in {
            name for issue in result.issues for name in issue.datasets
        }

    def test_user_catch_all_pattern_persists_boundaries(self, spaceflights):
        catalog = DataCatalog.from_config(
            {
                "{default}": {
                    "type": "pickle.PickleDataset",
                    "filepath": "s3://b/{default}.pkl",
                }
            }
        )

        assert validate_deployment_grouping(spaceflights, catalog)

    def test_namespaced_dataset_resolved_through_factory_pattern(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "a.table", name="make", namespace="a"),
                node(_identity, "a.table", "out", name="use", namespace="b"),
            ]
        )
        pattern = {
            "{namespace}.table": {
                "type": "pandas.ParquetDataset",
                "filepath": "s3://b/{namespace}.pq",
            }
        }

        assert validate_deployment_grouping(pipe, DataCatalog.from_config(pattern))
        assert _problems(validate_deployment_grouping(pipe, DataCatalog())) == [
            "ephemeral_boundary"
        ]

    def test_dataset_used_by_several_groups_lists_every_consumer(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "table", name="make", namespace="a"),
                node(_identity, "table", "out_b", name="use_b", namespace="b"),
                node(_identity, "table", "out_c", name="use_c", namespace="c"),
            ]
        )

        (issue,) = validate_deployment_grouping(pipe, DataCatalog()).errors

        assert issue.groups == ("a", "b", "c")
        assert "groups 'b', 'c'" in issue.message

    def test_transcoded_names_are_checked_separately(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "table@spark", name="make", namespace="a"),
                node(_identity, "table@pandas", "out", name="use", namespace="b"),
            ]
        )
        only_spark = DataCatalog.from_config({"table@spark": PERSISTED})
        both = DataCatalog.from_config(
            {"table@spark": PERSISTED, "table@pandas": PERSISTED}
        )

        (issue,) = validate_deployment_grouping(pipe, only_spark).errors
        assert issue.datasets == ("table@pandas",)
        assert validate_deployment_grouping(pipe, both)


class TestDatasetResolution:
    @pytest.mark.parametrize(
        "catalog, expected",
        [
            (DataCatalog(datasets={"table": MemoryDataset()}), ["ephemeral_boundary"]),
            (
                DataCatalog(datasets={"table": CachedDataset(MemoryDataset())}),
                ["ephemeral_boundary"],
            ),
            (
                DataCatalog(
                    datasets={"table": CachedDataset(_FileDataset("s3://b/t"))}
                ),
                [],
            ),
            (DataCatalog(datasets={"table": _FileDataset("s3://b/t")}), []),
            (
                DataCatalog(datasets={"table": _FileDataset("data/t.csv")}),
                ["local_boundary"],
            ),
            (
                DataCatalog(datasets={"table": _FileDataset("memory://t.csv")}),
                ["ephemeral_boundary"],
            ),
            (
                DataCatalog(datasets={"table": _PathDataset("data/parts")}),
                ["local_boundary"],
            ),
            (DataCatalog(datasets={"table": _PathDataset("s3://b/parts")}), []),
            (
                DataCatalog.from_config(
                    {"table": {"type": "CachedDataset", "dataset": PERSISTED}}
                ),
                [],
            ),
            (
                DataCatalog.from_config(
                    {
                        "table": {
                            "type": "CachedDataset",
                            "dataset": {"type": "MemoryDataset"},
                        }
                    }
                ),
                ["ephemeral_boundary"],
            ),
            (
                DataCatalog.from_config(
                    {"table": {"type": "CachedDataset", "dataset": MemoryDataset()}}
                ),
                ["ephemeral_boundary"],
            ),
            (
                DataCatalog.from_config({"table": {"type": MemoryDataset}}),
                ["ephemeral_boundary"],
            ),
            (
                DataCatalog.from_config(
                    {"table": {"type": "kedro.io.memory_dataset.MemoryDataset"}}
                ),
                ["ephemeral_boundary"],
            ),
            (
                DataCatalog.from_config(
                    {"table": {"type": "my_package.MemoryDataset"}}
                ),
                [],
            ),
            (
                DataCatalog.from_config(
                    {
                        "table": {
                            "type": "not_installed.FancyDataset",
                            "filepath": "s3://b/t",
                        }
                    }
                ),
                [],
            ),
            (
                DataCatalog.from_config(
                    {
                        "table": {
                            "type": "partitions.PartitionedDataset",
                            "path": "data/parts",
                        }
                    }
                ),
                ["local_boundary"],
            ),
            (SharedMemoryDataCatalog(), ["ephemeral_boundary"]),
            (_MinimalCatalog({}), ["ephemeral_boundary"]),
            (_MinimalCatalog({"table": MemoryDataset()}), ["ephemeral_boundary"]),
            (_MinimalCatalog({"table": _FileDataset("s3://b/t")}), []),
        ],
        ids=[
            "object-memory",
            "object-cached-memory",
            "object-cached-persisted",
            "object-cloud",
            "object-local",
            "object-memory-filesystem",
            "object-path-attribute-local",
            "object-path-attribute-cloud",
            "config-cached-persisted",
            "config-cached-memory-config",
            "config-cached-memory-object",
            "config-class-type",
            "config-full-module-path",
            "config-unrelated-memory-name",
            "config-type-not-installed",
            "config-path-key",
            "shared-memory-catalog",
            "no-resolver-missing",
            "no-resolver-memory",
            "no-resolver-cloud",
        ],
    )
    def test_dataset_resolution(self, two_groups, catalog, expected):
        assert _problems(validate_deployment_grouping(two_groups, catalog)) == expected


class TestLocalPaths:
    @pytest.mark.parametrize(
        "filepath",
        [
            "data/03_primary/table.parquet",
            "/tmp/table.parquet",
            "file:///tmp/table.parquet",
        ],
    )
    def test_local_path_is_a_warning(self, two_groups, filepath):
        catalog = DataCatalog.from_config(
            {"table": {"type": "pandas.ParquetDataset", "filepath": filepath}}
        )

        result = validate_deployment_grouping(two_groups, catalog)

        assert result
        (issue,) = result.warnings
        assert issue.code == "local_boundary"
        assert issue.datasets == ("table",)
        assert filepath in issue.message

    @pytest.mark.parametrize(
        "filepath",
        [
            "/dbfs/mnt/table.parquet",
            "/Volumes/catalog/schema/volume/table.parquet",
            "/Workspace/Users/someone/table.parquet",
            "dbfs:/mnt/table.parquet",
            "s3://bucket/table.parquet",
            "abfss://container@account.dfs.core.windows.net/table.parquet",
            "gcs://bucket/table.parquet",
        ],
    )
    def test_shared_storage_is_not_reported(self, two_groups, filepath):
        catalog = DataCatalog.from_config(
            {"table": {"type": "pandas.ParquetDataset", "filepath": filepath}}
        )

        assert validate_deployment_grouping(two_groups, catalog).issues == ()

    def test_boundary_without_filepath_is_not_reported(self, two_groups):
        catalog = DataCatalog.from_config(
            {"table": {"type": "pandas.SQLTableDataset", "table_name": "t"}}
        )

        assert validate_deployment_grouping(two_groups, catalog).issues == ()

    def test_in_process_filesystem_is_ephemeral(self, two_groups):
        catalog = DataCatalog.from_config(
            {"table": {"type": "pandas.CSVDataset", "filepath": "memory://table.csv"}}
        )

        (issue,) = validate_deployment_grouping(two_groups, catalog).errors
        assert issue.code == "ephemeral_boundary"
        assert issue.datasets == ("table",)

    @pytest.mark.parametrize(
        "filepath",
        ["DBFS:/mnt/table.parquet", "/volumes/catalog/schema/volume/table.parquet"],
    )
    def test_shared_storage_prefixes_ignore_case(self, two_groups, filepath):
        catalog = DataCatalog.from_config(
            {"table": {"type": "pandas.ParquetDataset", "filepath": filepath}}
        )

        assert validate_deployment_grouping(two_groups, catalog).issues == ()


class TestLazyAndMaterialisedDatasetsAgree:
    @pytest.mark.parametrize(
        "config, expected",
        [
            ({"type": "pandas.ParquetDataset", "filepath": "s3://b/table.parquet"}, []),
            (
                {"type": "pandas.ParquetDataset", "filepath": "data/table.parquet"},
                ["local_boundary"],
            ),
            (
                {
                    "type": "partitions.PartitionedDataset",
                    "path": "data/parts",
                    "dataset": "pandas.CSVDataset",
                },
                ["local_boundary"],
            ),
            (
                {
                    "type": "partitions.PartitionedDataset",
                    "path": "s3://b/parts",
                    "dataset": "pandas.CSVDataset",
                },
                [],
            ),
            (
                {"type": "pandas.CSVDataset", "filepath": "memory://table.csv"},
                ["ephemeral_boundary"],
            ),
            ({"type": "MemoryDataset"}, ["ephemeral_boundary"]),
        ],
        ids=[
            "cloud",
            "local",
            "partitioned-local",
            "partitioned-cloud",
            "memory-filesystem",
            "memory-dataset",
        ],
    )
    def test_same_issues_before_and_after_materialising(
        self, two_groups, config, expected
    ):
        lazy = DataCatalog.from_config({"table": config})
        materialised = DataCatalog.from_config({"table": config})
        materialised["table"]

        assert _problems(validate_deployment_grouping(two_groups, lazy)) == expected
        assert (
            _problems(validate_deployment_grouping(two_groups, materialised))
            == expected
        )


class TestGroupCycles:
    def test_interrupted_namespace_is_a_cycle(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "first", name="a", namespace="x"),
                node(_identity, "first", "second", name="b"),
                node(_identity, "second", "third", name="c", namespace="x"),
            ]
        )
        catalog = DataCatalog.from_config({"first": PERSISTED, "second": PERSISTED})

        result = validate_deployment_grouping(pipe, catalog)

        assert not result
        (issue,) = result.errors
        assert issue.code == "group_cycle"
        assert set(issue.groups) == {"x", "b"}
        assert "->" in issue.message


class TestSingleNodeGroups:
    def test_ungrouped_nodes_are_reported_as_info(self, spaceflights):
        catalog = DataCatalog.from_config(
            {
                "{default}": {
                    "type": "pickle.PickleDataset",
                    "filepath": "s3://b/{default}.pkl",
                }
            }
        )

        result = validate_deployment_grouping(spaceflights, catalog, group_by=None)

        assert result
        (issue,) = result.issues
        assert issue.code == "single_node_groups"
        assert issue.severity == "info"
        assert len(issue.groups) == len(spaceflights.nodes)
        assert issue.nodes == issue.groups

    def test_namespace_groups_are_not_reported(self, spaceflights):
        catalog = DataCatalog.from_config({"model_input_table": PERSISTED})

        assert "single_node_groups" not in _issue_codes(
            validate_deployment_grouping(spaceflights, catalog)
        )


class TestExplicitGroups:
    @staticmethod
    def _groups(*spec: tuple[str, list[str]]) -> list[GroupedNodes]:
        return [
            GroupedNodes(name=name, type="nodes", nodes=nodes) for name, nodes in spec
        ]

    def test_explicit_groups_are_used_instead_of_group_by(self, two_groups):
        groups = self._groups(("everything", TWO_GROUPS_NODES))

        result = validate_deployment_grouping(
            two_groups, DataCatalog(), groups=groups, group_by=None
        )

        assert result
        assert result.groups == ("everything",)

    @pytest.mark.parametrize(
        "spec, message",
        [
            (
                (("g", TWO_GROUPS_NODES[:2]), ("g", TWO_GROUPS_NODES[2:])),
                "used more than once",
            ),
            ((("g", TWO_GROUPS_NODES), ("empty", [])), "contain no nodes"),
            ((("g", [*TWO_GROUPS_NODES, "ghost"]),), "not in the pipeline"),
            ((("g", TWO_GROUPS_NODES), ("h", ["b.use"])), "more than one group"),
            ((("g", TWO_GROUPS_NODES[:2]),), "not in any group"),
        ],
        ids=[
            "repeated-name",
            "empty-group",
            "unknown-node",
            "node-in-two-groups",
            "missing-node",
        ],
    )
    def test_invalid_grouping_skips_other_checks(self, two_groups, spec, message):
        result = validate_deployment_grouping(
            two_groups, DataCatalog(), groups=self._groups(*spec)
        )

        assert not result
        assert {issue.code for issue in result.issues} == {"invalid_grouping"}
        assert any(message in issue.message for issue in result.errors)


class TestResult:
    @pytest.fixture
    def mixed_result(self):
        pipe = Pipeline(
            [
                node(
                    _identity,
                    "raw",
                    ["a_local", "b_memory"],
                    name="make",
                    namespace="a",
                ),
                node(
                    _combine, ["a_local", "b_memory"], "out", name="use", namespace="b"
                ),
            ]
        )
        catalog = DataCatalog.from_config(
            {"a_local": {"type": "pandas.ParquetDataset", "filepath": "data/a.parquet"}}
        )
        return validate_deployment_grouping(pipe, catalog)

    def test_issues_are_ordered_by_severity(self, mixed_result):
        assert [issue.severity for issue in mixed_result.issues] == [
            "error",
            "warning",
            "info",
        ]
        assert len(mixed_result.errors) == 1
        assert len(mixed_result.warnings) == 1

    def test_to_dict_is_json_serialisable(self, mixed_result):
        data = json.loads(json.dumps(mixed_result.to_dict()))

        assert data["status"] == "failed"
        assert data["groups"] == ["a", "b"]
        assert data["issues"][0] == {
            "code": "ephemeral_boundary",
            "severity": "error",
            "message": mixed_result.errors[0].message,
            "datasets": ["b_memory"],
            "groups": ["a", "b"],
            "nodes": [],
        }

    def test_raise_if_failed_raises_with_messages(self, mixed_result):
        with pytest.raises(DeploymentGroupingError, match="b_memory") as exc_info:
            mixed_result.raise_if_failed()

        assert exc_info.value.result is mixed_result

    def test_raise_if_failed_is_silent_when_passed(self, two_groups):
        result = validate_deployment_grouping(
            two_groups, DataCatalog.from_config({"table": PERSISTED})
        )

        result.raise_if_failed()

    def test_public_api(self):
        for name in (
            "DeploymentGroupingIssue",
            "DeploymentGroupingError",
            "DeploymentGroupingResult",
            "validate_deployment_grouping",
        ):
            assert name in inspection.__all__
