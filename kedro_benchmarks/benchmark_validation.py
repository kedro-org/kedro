import dataclasses
import inspect
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from kedro.framework.context import KedroContext
from kedro.pipeline import node, pipeline
from kedro.validation.model_factory import instantiate_model
from kedro.validation.parameter_validator import ParameterValidator
from kedro.validation.type_extractor import TypeExtractor


class BenchmarkPydanticModel(BaseModel):
    field_0: int
    field_1: str
    field_2: float
    field_3: bool
    field_4: list[int]


@dataclasses.dataclass
class BenchmarkDataclassModel:
    field_0: int
    field_1: str
    field_2: float
    field_3: bool
    field_4: list[int]


class _BenchmarkConfigLoader:
    def __init__(self, parameters: dict[str, Any]) -> None:
        self._parameters = parameters

    def __getitem__(self, key: str) -> dict[str, Any]:
        if key == "parameters":
            return self._parameters
        return {}


def _make_raw_value(index: int) -> dict[str, Any]:
    return {
        "field_0": index,
        "field_1": f"value_{index}",
        "field_2": index / 10,
        "field_3": bool(index % 2),
        "field_4": [index, index + 1, index + 2],
    }


def _make_node_func(name: str, model_type: type, typed_params_per_node: int):
    def typed_node(*args):
        return None

    typed_node.__name__ = name
    typed_node.__annotations__ = {
        f"options_{index}": model_type for index in range(typed_params_per_node)
    }
    typed_node.__annotations__["return"] = None
    typed_node.__signature__ = inspect.Signature(
        [
            inspect.Parameter(
                f"options_{index}",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
            for index in range(typed_params_per_node)
        ]
    )
    return typed_node


def _make_pipeline(node_count: int, typed_params_per_node: int = 1):
    nodes = []
    for node_index in range(node_count):
        node_func = _make_node_func(
            f"typed_node_{node_index}",
            BenchmarkPydanticModel,
            typed_params_per_node,
        )
        node_inputs = [
            f"params:model_options_{node_index}_{param_index}"
            for param_index in range(typed_params_per_node)
        ]
        nodes.append(
            node(
                node_func,
                node_inputs,
                f"output_{node_index}",
                name=f"typed_node_{node_index}",
            )
        )
    return pipeline(nodes)


def _make_pipeline_dict(node_count: int, typed_params_per_node: int = 1):
    return {"data_science": _make_pipeline(node_count, typed_params_per_node)}


def _make_raw_params(node_count: int, typed_params_per_node: int = 1):
    return {
        f"model_options_{node_index}_{param_index}": _make_raw_value(
            node_index + param_index
        )
        for node_index in range(node_count)
        for param_index in range(typed_params_per_node)
    }


class InstantiateModelTimeSuite:
    params = ("pydantic", "dataclass")
    param_names = ("model_kind",)

    def setup(self, model_kind):
        self.raw_value = _make_raw_value(1)
        self.model_type = (
            BenchmarkPydanticModel
            if model_kind == "pydantic"
            else BenchmarkDataclassModel
        )

    def time_instantiate_model(self, model_kind):
        instantiate_model("model_options", self.raw_value, self.model_type)


class TypeExtractorTimeSuite:
    params = ([10, 100, 500], [1, 5])
    param_names = ("node_count", "typed_params_per_node")

    def setup(self, node_count, typed_params_per_node):
        self.pipelines = _make_pipeline_dict(node_count, typed_params_per_node)

    def time_extract_types_from_pipelines(self, node_count, typed_params_per_node):
        TypeExtractor(self.pipelines).extract_types_from_pipelines()


class ParameterValidatorTimeSuite:
    params = ([10, 100, 500], [1, 5])
    param_names = ("node_count", "typed_params_per_node")

    def setup(self, node_count, typed_params_per_node):
        self.pipelines = _make_pipeline_dict(node_count, typed_params_per_node)
        self.raw_params = _make_raw_params(node_count, typed_params_per_node)
        self.validator = ParameterValidator(self.pipelines)

    def time_validate_raw_params(self, node_count, typed_params_per_node):
        self.validator.validate_raw_params(self.raw_params)


class ContextParamsTimeSuite:
    params = ([10, 100, 500], [1, 5])
    param_names = ("node_count", "typed_params_per_node")

    def setup(self, node_count, typed_params_per_node):
        import kedro.framework.project as project_module

        self.project_module = project_module
        self.original_pipelines = project_module.pipelines
        self.pipelines = _make_pipeline_dict(node_count, typed_params_per_node)
        project_module.pipelines = self.pipelines

        self.context = KedroContext(
            project_path=Path.cwd(),
            config_loader=_BenchmarkConfigLoader(
                _make_raw_params(node_count, typed_params_per_node)
            ),
            env="base",
            package_name="benchmark_project",
            hook_manager=None,
        )
        self.cached_context = KedroContext(
            project_path=Path.cwd(),
            config_loader=_BenchmarkConfigLoader(
                _make_raw_params(node_count, typed_params_per_node)
            ),
            env="base",
            package_name="benchmark_project",
            hook_manager=None,
        )
        self.cached_context.params

    def teardown(self, node_count, typed_params_per_node):
        self.project_module.pipelines = self.original_pipelines

    def time_context_params_uncached(self, node_count, typed_params_per_node):
        self.context._validated_params_cache = None
        self.context._cached_validation_scope = None
        self.context.params

    def time_context_params_cached(self, node_count, typed_params_per_node):
        self.cached_context.params
