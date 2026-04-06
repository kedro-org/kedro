"""Tests for kedro.validation.type_extractor."""

from __future__ import annotations

import dataclasses
import inspect
from unittest.mock import MagicMock, patch

from kedro.pipeline import node as kedro_node
from kedro.validation.type_extractor import TypeExtractor

from .conftest import SampleDataclass, SamplePydanticModel


@dataclasses.dataclass
class _TypeA:
    x: int


@dataclasses.dataclass
class _TypeB:
    y: str


class TestExtractTypesFromPipelines:
    def test_empty_pipelines(self):
        extractor = TypeExtractor(pipelines={})
        result = extractor.extract_types_from_pipelines()
        assert result == {}

    def test_skips_default_pipeline(self):
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

        extractor = TypeExtractor(
            pipelines={
                "__default__": default_pipeline,
                "data_science": data_science_pipeline,
            }
        )
        result = extractor.extract_types_from_pipelines()

        assert "eval_config" in result
        assert "default_only" not in result

    def test_successful_extraction(self):
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

        extractor = TypeExtractor(pipelines={"data_science": pipeline})
        result = extractor.extract_types_from_pipelines()

        assert "eval_config" in result
        assert result["eval_config"] == SampleDataclass

    def test_conflicting_types_warns(self, caplog):
        """When two pipelines define different types for the same key, warn."""

        def func_a(opts: _TypeA) -> None:
            pass

        def func_b(opts: _TypeB) -> None:
            pass

        node_a = kedro_node(
            func=func_a,
            inputs="params:shared_config",
            outputs="output_a",
            name="node_a",
        )
        node_b = kedro_node(
            func=func_b,
            inputs="params:shared_config",
            outputs="output_b",
            name="node_b",
        )

        pipeline_a = MagicMock()
        pipeline_a.nodes = [node_a]
        pipeline_b = MagicMock()
        pipeline_b.nodes = [node_b]

        extractor = TypeExtractor(
            pipelines={"pipeline_a": pipeline_a, "pipeline_b": pipeline_b}
        )

        with caplog.at_level("WARNING"):
            result = extractor.extract_types_from_pipelines()

        assert "shared_config" in result
        assert "Conflicting type requirements" in caplog.text

    def test_union_type_annotation_does_not_crash(self):
        """types.UnionType (int | str) lacks __name__; extraction must not raise AttributeError."""

        def my_func(value: int | str) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:my_param",
            outputs="output",
            name="test_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"pipeline_a": pipeline})
        result = extractor.extract_types_from_pipelines()

        assert "my_param" in result

    def test_conflicting_union_type_annotations_does_not_crash(self, caplog):
        """Conflicting types.UnionType annotations across pipelines must not raise AttributeError."""

        def func_a(value: int | str) -> None:
            pass

        def func_b(value: int | float) -> None:
            pass

        node_a = kedro_node(
            func=func_a,
            inputs="params:shared_param",
            outputs="out_a",
            name="node_a",
        )
        node_b = kedro_node(
            func=func_b,
            inputs="params:shared_param",
            outputs="out_b",
            name="node_b",
        )

        pipeline_a = MagicMock()
        pipeline_a.nodes = [node_a]
        pipeline_b = MagicMock()
        pipeline_b.nodes = [node_b]

        extractor = TypeExtractor(
            pipelines={"pipeline_a": pipeline_a, "pipeline_b": pipeline_b}
        )

        with caplog.at_level("WARNING"):
            result = extractor.extract_types_from_pipelines()

        assert "shared_param" in result
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
        """Uses MagicMock because real Node validates dict keys against
        function signature, which conflicts with the dataset->arg mapping
        format used by the type extractor.
        """

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
        """Uses MagicMock because real Node validates dict keys against
        function signature.
        """

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
