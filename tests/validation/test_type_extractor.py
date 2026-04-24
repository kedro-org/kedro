"""Tests for kedro.validation.type_extractor."""

from __future__ import annotations

import dataclasses
import inspect
from typing import Optional, Union
from unittest.mock import MagicMock, patch

from kedro.pipeline import node as kedro_node
from kedro.validation.type_extractor import TypeExtractor, _type_name

from .conftest import SampleDataclass, SamplePydanticModel


@dataclasses.dataclass
class _TypeA:
    x: int


@dataclasses.dataclass
class _TypeB:
    y: str


# Module-level types for tests
_UnionType = list[str] | None
_OptionalPydantic = SamplePydanticModel | None
_OptionalDataclass = SampleDataclass | None
_MultiModelUnion = SamplePydanticModel | SampleDataclass


class TestTypeName:
    def test_regular_type_uses_name(self):
        assert _type_name(int) == "int"

    def test_class_uses_name(self):
        assert _type_name(SampleDataclass) == "SampleDataclass"

    def test_union_pipe_syntax_uses_str(self):
        tp = list[str] | int
        assert _type_name(tp) == "list[str] | int"

    def test_typing_union_uses_str(self):
        # str(Union[...]) format varies by Python version; verify str() is called, not __name__
        tp = Union[str, int]  # noqa: UP007
        assert _type_name(tp) == str(tp)
        assert _type_name(tp) != "Union"

    def test_optional_uses_str(self):
        # str(Optional[...]) format varies by Python version; verify str() is called, not __name__
        tp = Optional[str]  # noqa: UP007
        assert _type_name(tp) == str(tp)
        assert _type_name(tp) != "Union"

    def test_generic_alias_uses_name(self):
        # list[str] is a GenericAlias with __name__ == "list"
        assert _type_name(list[str]) == "list"


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

    def test_conflicting_types_getattr_fallback(self, caplog):
        """The warning should not crash if a type lacks __name__."""
        nameless_type = list[str] | int  # UnionType has no __name__

        pipeline_a = MagicMock()
        pipeline_b = MagicMock()

        extractor = TypeExtractor(
            pipelines={"pipeline_a": pipeline_a, "pipeline_b": pipeline_b}
        )

        # Patch _extract_types_from_pipeline to return types without __name__
        returns = iter([{"key": nameless_type}, {"key": _TypeA}])
        with patch.object(
            extractor,
            "_extract_types_from_pipeline",
            side_effect=lambda _: next(returns),
        ):
            with caplog.at_level("WARNING"):
                result = extractor.extract_types_from_pipelines()

        assert "Conflicting type requirements" in caplog.text
        assert "list[str] | int" in caplog.text
        assert "key" in result

    def test_mixed_type_hints_only_records_validatable(self):
        """Only Pydantic/dataclass types should be recorded, not builtins or unions.
        Optional[Model] should be unwrapped and recorded.
        """

        def pydantic_func(config: SamplePydanticModel) -> None:
            pass

        def dataclass_func(opts: SampleDataclass) -> None:
            pass

        def builtin_func(threshold: int) -> None:
            pass

        def union_func(data: _UnionType) -> None:
            pass

        def optional_func(cfg: _OptionalPydantic) -> None:
            pass

        nodes = [
            kedro_node(
                func=pydantic_func,
                inputs="params:pydantic_cfg",
                outputs="o1",
                name="n1",
            ),
            kedro_node(
                func=dataclass_func, inputs="params:dc_cfg", outputs="o2", name="n2"
            ),
            kedro_node(
                func=builtin_func, inputs="params:threshold", outputs="o3", name="n3"
            ),
            kedro_node(
                func=union_func, inputs="params:union_cfg", outputs="o4", name="n4"
            ),
            kedro_node(
                func=optional_func,
                inputs="params:optional_cfg",
                outputs="o5",
                name="n5",
            ),
        ]

        pipeline = MagicMock()
        pipeline.nodes = nodes

        extractor = TypeExtractor(pipelines={"test_pipeline": pipeline})
        result = extractor.extract_types_from_pipelines()

        assert "pydantic_cfg" in result
        assert result["pydantic_cfg"] == SamplePydanticModel
        assert "dc_cfg" in result
        assert result["dc_cfg"] == SampleDataclass
        assert "optional_cfg" in result
        assert result["optional_cfg"] == SamplePydanticModel
        assert "threshold" not in result
        assert "union_cfg" not in result


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

    def test_union_type_hint_skipped(self, type_extractor):
        def my_func(data: _UnionType) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:config",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert result == {}

    def test_optional_pydantic_unwrapped(self, type_extractor):
        """Optional[PydanticModel] should unwrap to PydanticModel and be recorded."""

        def my_func(config: _OptionalPydantic) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:config",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert "config" in result
        assert result["config"] == SamplePydanticModel

    def test_optional_dataclass_unwrapped(self, type_extractor):
        """Optional[Dataclass] should unwrap to Dataclass and be recorded."""

        def my_func(config: _OptionalDataclass) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:config",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert "config" in result
        assert result["config"] == SampleDataclass

    def test_builtin_type_hint_skipped(self, type_extractor):
        def my_func(data: int) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:threshold",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert result == {}

    def test_plain_dict_type_hint_skipped(self, type_extractor):
        def my_func(data: dict) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:config",
            outputs="output",
            name="test_node",
        )

        result = type_extractor._extract_types_from_node(test_node)
        assert result == {}

    def test_multi_model_union_warns(self, type_extractor, caplog):
        """A union of multiple models should warn that validation is skipped."""

        def my_func(options: _MultiModelUnion) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:split_options",
            outputs="output",
            name="test_node",
        )

        with caplog.at_level("WARNING"):
            result = type_extractor._extract_types_from_node(test_node)

        assert result == {}
        assert "SamplePydanticModel | SampleDataclass" in caplog.text
        assert "not supported for validation" in caplog.text

    def test_multi_model_union_warns_once(self, type_extractor, caplog):
        """The union warning should only fire once per union type."""

        def func_a(options: _MultiModelUnion) -> None:
            pass

        def func_b(options: _MultiModelUnion) -> None:
            pass

        node_a = kedro_node(
            func=func_a,
            inputs="params:split_options",
            outputs="output_a",
            name="node_a",
        )
        node_b = kedro_node(
            func=func_b,
            inputs="params:ns.split_options",
            outputs="output_b",
            name="node_b",
        )

        with caplog.at_level("WARNING"):
            type_extractor._extract_types_from_node(node_a)
            type_extractor._extract_types_from_node(node_b)

        assert caplog.text.count("SamplePydanticModel | SampleDataclass") == 1


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
