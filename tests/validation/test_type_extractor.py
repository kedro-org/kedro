"""Tests for kedro.validation.type_extractor."""

from __future__ import annotations

import dataclasses
import inspect
from unittest.mock import MagicMock, patch

from kedro.pipeline import node as kedro_node

from .conftest import SampleDataclass, SamplePydanticModel


@dataclasses.dataclass
class _TypeA:
    x: int


@dataclasses.dataclass
class _TypeB:
    y: str


class TestExtractTypesFromPipelines:
    def test_import_error_returns_empty(self, type_extractor):
        with patch.dict("sys.modules", {"kedro.framework.project": None}):
            result = type_extractor.extract_types_from_pipelines()
        assert result == {}

    def test_general_exception_returns_empty(self, type_extractor):
        with patch(
            "kedro.framework.project.pipelines",
            new_callable=lambda: type(
                "BadPipelines",
                (),
                {"__iter__": lambda self: (_ for _ in ()).throw(RuntimeError("boom"))},
            ),
            create=True,
        ):
            result = type_extractor.extract_types_from_pipelines()
        assert result == {}

    def test_skips_default_pipeline(self, type_extractor):
        def my_func(options: SampleDataclass) -> None:
            pass

        def default_func(config: SamplePydanticModel) -> None:
            pass

        data_science_node = kedro_node(
            func=my_func,
            inputs="params:eval_config",
            outputs="output",
            name="ds_node",
        )
        default_node = kedro_node(
            func=default_func,
            inputs="params:default_only",
            outputs="default_output",
            name="default_node",
        )

        default_pipeline = MagicMock()
        default_pipeline.nodes = [default_node]

        data_science_pipeline = MagicMock()
        data_science_pipeline.nodes = [data_science_node]

        with patch(
            "kedro.framework.project.pipelines",
            {"__default__": default_pipeline, "data_science": data_science_pipeline},
        ):
            result = type_extractor.extract_types_from_pipelines()

        assert "eval_config" in result
        assert "default_only" not in result

    def test_successful_extraction(self, type_extractor):
        def my_func(options: SampleDataclass) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:eval_config",
            outputs="output",
            name="test_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        with patch(
            "kedro.framework.project.pipelines",
            {"data_science": pipeline},
        ):
            result = type_extractor.extract_types_from_pipelines()

        assert "eval_config" in result
        assert result["eval_config"] == SampleDataclass

    def test_conflicting_types_warns(self, type_extractor, caplog):
        """When two pipelines define different types for the same key, warn.

        Uses MagicMock because get_type_hints cannot resolve types
        defined inside a function scope.
        """
        node_a = MagicMock()
        node_a.func = lambda opts: None
        node_a.func.__annotations__ = {"opts": _TypeA}
        node_a.func.__name__ = "func_a"
        node_a.inputs = ["params:shared_config"]

        node_b = MagicMock()
        node_b.func = lambda opts: None
        node_b.func.__annotations__ = {"opts": _TypeB}
        node_b.func.__name__ = "func_b"
        node_b.inputs = ["params:shared_config"]

        pipeline_a = MagicMock()
        pipeline_a.nodes = [node_a]
        pipeline_b = MagicMock()
        pipeline_b.nodes = [node_b]

        with (
            patch(
                "kedro.framework.project.pipelines",
                {"pipeline_a": pipeline_a, "pipeline_b": pipeline_b},
            ),
            caplog.at_level("WARNING"),
        ):
            result = type_extractor.extract_types_from_pipelines()

        assert "shared_config" in result
        assert "Conflicting type requirements" in caplog.text


class TestExtractTypesFromNode:
    def test_no_func_attribute(self, type_extractor):
        node = MagicMock(spec=[])
        result = type_extractor._extract_types_from_node(node)
        assert result == {}

    def test_signature_extraction_error(self, type_extractor):
        def bad_func() -> None:
            pass

        test_node = kedro_node(
            func=bad_func, inputs=None, outputs="output", name="bad_node"
        )

        with patch(
            "kedro.validation.type_extractor.get_type_hints",
            side_effect=TypeError("boom"),
        ):
            result = type_extractor._extract_types_from_node(test_node)
        assert result == {}

    def test_typed_param_input(self, type_extractor):
        def my_func(data: SamplePydanticModel) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:model_options",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert "model_options" in result
        assert result["model_options"] == SamplePydanticModel

    def test_untyped_param_input(self, type_extractor):
        def my_func(data) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:model_options",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert result == {}

    def test_non_param_input_ignored(self, type_extractor):
        def my_func(data: SampleDataclass) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="companies",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert result == {}

    def test_dict_inputs(self, type_extractor):
        def my_func(options: SampleDataclass) -> None:
            pass

        node = MagicMock()
        node.func = my_func
        node.inputs = {"params:eval_config": "options"}

        result = type_extractor._extract_types_from_node(node)
        assert "eval_config" in result
        assert result["eval_config"] == SampleDataclass


class TestExtractTypesFromPipeline:
    def test_pipeline_with_nodes(self, type_extractor):
        def my_func(options: SampleDataclass) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:eval_config",
            outputs="output",
            name="test_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        result = type_extractor._extract_types_from_pipeline(pipeline)
        assert "eval_config" in result

    def test_pipeline_no_nodes_attribute(self, type_extractor):
        pipeline = MagicMock(spec=[])
        result = type_extractor._extract_types_from_pipeline(pipeline)
        assert result == {}


class TestBuildDatasetToArgMapping:
    def test_dict_inputs(self, type_extractor):
        def my_func(a, b):
            pass

        node = MagicMock()
        node.inputs = {"ds_a": "a", "ds_b": "b"}
        sig = inspect.signature(my_func)

        result = type_extractor._build_dataset_to_arg_mapping(node, sig)
        assert result == {"ds_a": "a", "ds_b": "b"}

    def test_list_inputs(self, type_extractor):
        def my_func(a, b):
            pass

        test_node = kedro_node(
            func=my_func,
            inputs=["ds_a", "ds_b"],
            outputs="output",
            name="test_node",
        )

        sig = inspect.signature(my_func)
        result = type_extractor._build_dataset_to_arg_mapping(test_node, sig)
        assert result == {"ds_a": "a", "ds_b": "b"}

    def test_no_inputs(self, type_extractor):
        def my_func():
            pass

        test_node = kedro_node(
            func=my_func, inputs=None, outputs="output", name="test_node"
        )

        sig = inspect.signature(my_func)
        result = type_extractor._build_dataset_to_arg_mapping(test_node, sig)
        assert result == {}
