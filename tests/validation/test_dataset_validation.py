"""Tests for dataset validation using Pandera DataFrameModel schemas."""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pandera as pa
import pytest

from kedro.pipeline import node as kedro_node
from kedro.validation.dataset_validator import (
    DataValidationError,
    _is_pandera_model,
    _ValidatingDataset,
    validate_dataframe,
)
from kedro.validation.type_extractor import TypeExtractor

from .conftest import SampleDataclass, SamplePydanticModel

# --- Module-level Pandera schemas (required for get_type_hints) ---


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(nullable=False, unique=True)
    total_fleet_count: float = pa.Field(ge=0)

    class Config:
        strict = False


class ShuttlesSchema(pa.DataFrameModel):
    shuttle_id: int = pa.Field(nullable=False)
    capacity: int = pa.Field(gt=0)

    class Config:
        strict = False


# --- TestIsPanderaModel ---


class TestIsPanderaModel:
    def test_pandera_model_class(self):
        assert _is_pandera_model(CompaniesSchema) is True

    def test_pydantic_model_class(self):
        assert _is_pandera_model(SamplePydanticModel) is False

    def test_dataclass(self):
        assert _is_pandera_model(SampleDataclass) is False

    def test_builtin_type(self):
        assert _is_pandera_model(dict) is False

    def test_non_class(self):
        assert _is_pandera_model("not a class") is False


# --- TestExtractDatasetSchemas ---


class TestExtractDatasetSchemas:
    def test_discovers_pandera_annotated_inputs(self):
        def preprocess_companies(companies: CompaniesSchema) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=preprocess_companies,
            inputs="companies",
            outputs="preprocessed_companies",
            name="preprocess_companies",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"data_processing": pipeline})
        result = extractor.extract_dataset_schemas()

        assert "companies" in result
        assert result["companies"] is CompaniesSchema

    def test_ignores_params_inputs(self):
        def train(params: CompaniesSchema) -> None:
            pass

        test_node = kedro_node(
            func=train,
            inputs="params:training_config",
            outputs="model",
            name="train_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"training": pipeline})
        result = extractor.extract_dataset_schemas()

        assert result == {}

    def test_ignores_non_pandera_annotations(self):
        def process(data: pd.DataFrame) -> pd.DataFrame:
            return data

        test_node = kedro_node(
            func=process,
            inputs="raw_data",
            outputs="processed_data",
            name="process_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"pipeline": pipeline})
        result = extractor.extract_dataset_schemas()

        assert result == {}

    def test_ignores_untyped_inputs(self):
        def process(data) -> pd.DataFrame:
            return data

        test_node = kedro_node(
            func=process,
            inputs="raw_data",
            outputs="processed_data",
            name="process_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"pipeline": pipeline})
        result = extractor.extract_dataset_schemas()

        assert result == {}

    def test_mixed_inputs_pandera_and_pydantic(self):
        """A node with both a Pandera dataset input and a Pydantic params input."""

        def train(
            companies: CompaniesSchema, params: SamplePydanticModel
        ) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=train,
            inputs=["companies", "params:model_options"],
            outputs="model",
            name="train_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"training": pipeline})

        # Dataset schemas should find the Pandera input
        dataset_schemas = extractor.extract_dataset_schemas()
        assert "companies" in dataset_schemas
        assert dataset_schemas["companies"] is CompaniesSchema

        # Parameter types should find the Pydantic input
        param_types = extractor.extract_types_from_pipelines()
        assert "model_options" in param_types
        assert param_types["model_options"] is SamplePydanticModel

    def test_skips_default_pipeline(self):
        def preprocess(companies: CompaniesSchema) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=preprocess,
            inputs="companies",
            outputs="output",
            name="preprocess",
        )

        default_pipeline = MagicMock()
        default_pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"__default__": default_pipeline})
        result = extractor.extract_dataset_schemas()

        assert result == {}

    def test_empty_pipelines(self):
        extractor = TypeExtractor(pipelines={})
        result = extractor.extract_dataset_schemas()

        assert result == {}

    def test_multiple_datasets_on_same_node(self):
        def join(companies: CompaniesSchema, shuttles: ShuttlesSchema) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=join,
            inputs=["companies", "shuttles"],
            outputs="joined",
            name="join_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"pipeline": pipeline})
        result = extractor.extract_dataset_schemas()

        assert result["companies"] is CompaniesSchema
        assert result["shuttles"] is ShuttlesSchema

    def test_no_func_attribute(self):
        node = MagicMock(spec=[])

        extractor = TypeExtractor(pipelines={})
        result = extractor._extract_dataset_schemas_from_node(node)

        assert result == {}

    def test_dict_inputs(self):
        """Uses MagicMock because real Node validates dict keys."""

        def preprocess(companies: CompaniesSchema) -> pd.DataFrame:
            return companies

        node = MagicMock()
        node.func = preprocess
        node.inputs = {"companies": "companies"}

        extractor = TypeExtractor(pipelines={})
        result = extractor._extract_dataset_schemas_from_node(node)

        assert "companies" in result
        assert result["companies"] is CompaniesSchema


# --- TestValidateDataframe ---


class TestValidateDataframe:
    def test_valid_data_passes(self):
        df = pd.DataFrame({"id": [1, 2, 3], "total_fleet_count": [10.0, 20.0, 30.0]})

        result = validate_dataframe("companies", df, CompaniesSchema)

        pd.testing.assert_frame_equal(result, df)

    def test_invalid_data_raises_error(self):
        df = pd.DataFrame(
            {
                "id": [1, 1, 3],  # duplicates violate unique=True
                "total_fleet_count": [-5.0, 20.0, 30.0],  # negative violates ge=0
            }
        )

        with pytest.raises(DataValidationError, match="companies"):
            validate_dataframe("companies", df, CompaniesSchema)

    def test_non_pandera_schema_skipped(self):
        df = pd.DataFrame({"a": [1, 2, 3]})

        result = validate_dataframe("my_dataset", df, SamplePydanticModel)

        pd.testing.assert_frame_equal(result, df)

    def test_error_message_includes_dataset_and_schema_name(self):
        df = pd.DataFrame({"id": [1, 1], "total_fleet_count": [-1.0, 2.0]})

        with pytest.raises(DataValidationError) as exc_info:
            validate_dataframe("companies", df, CompaniesSchema)

        error_msg = str(exc_info.value)
        assert "companies" in error_msg
        assert "CompaniesSchema" in error_msg


# --- TestEndToEnd ---


class TestEndToEnd:
    def test_full_flow_discover_and_validate(self):
        """TypeExtractor discovers schema, then validate_dataframe validates."""

        def preprocess_companies(companies: CompaniesSchema) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=preprocess_companies,
            inputs="companies",
            outputs="preprocessed_companies",
            name="preprocess_companies",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"data_processing": pipeline})
        schemas = extractor.extract_dataset_schemas()

        assert "companies" in schemas

        # Valid data
        valid_df = pd.DataFrame(
            {"id": [1, 2, 3], "total_fleet_count": [10.0, 20.0, 30.0]}
        )
        result = validate_dataframe("companies", valid_df, schemas["companies"])
        pd.testing.assert_frame_equal(result, valid_df)

        # Invalid data
        invalid_df = pd.DataFrame({"id": [1, 1], "total_fleet_count": [-1.0, 2.0]})
        with pytest.raises(DataValidationError):
            validate_dataframe("companies", invalid_df, schemas["companies"])

    def test_both_param_and_dataset_validation_coexist(self):
        """Parameter validation and dataset validation work on the same pipeline."""

        def train(
            companies: CompaniesSchema, params: SamplePydanticModel
        ) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=train,
            inputs=["companies", "params:model_options"],
            outputs="model",
            name="train_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        extractor = TypeExtractor(pipelines={"training": pipeline})

        # Both types of extraction work independently
        dataset_schemas = extractor.extract_dataset_schemas()
        param_types = extractor.extract_types_from_pipelines()

        assert "companies" in dataset_schemas
        assert dataset_schemas["companies"] is CompaniesSchema
        assert "model_options" in param_types
        assert param_types["model_options"] is SamplePydanticModel

        # Dataset validation works
        valid_df = pd.DataFrame({"id": [1, 2], "total_fleet_count": [10.0, 20.0]})
        result = validate_dataframe("companies", valid_df, dataset_schemas["companies"])
        pd.testing.assert_frame_equal(result, valid_df)


# --- TestValidatingDataset ---


class TestValidatingDataset:
    def test_load_validates_and_returns_data(self):
        valid_df = pd.DataFrame(
            {"id": [1, 2, 3], "total_fleet_count": [10.0, 20.0, 30.0]}
        )
        mock_dataset = MagicMock()
        mock_dataset.load.return_value = valid_df

        wrapper = _ValidatingDataset(mock_dataset, CompaniesSchema, "companies")
        result = wrapper.load()

        mock_dataset.load.assert_called_once()
        pd.testing.assert_frame_equal(result, valid_df)

    def test_load_raises_on_invalid_data(self):
        invalid_df = pd.DataFrame({"id": [1, 1], "total_fleet_count": [-1.0, 2.0]})
        mock_dataset = MagicMock()
        mock_dataset.load.return_value = invalid_df

        wrapper = _ValidatingDataset(mock_dataset, CompaniesSchema, "companies")

        with pytest.raises(DataValidationError, match="companies"):
            wrapper.load()

    def test_save_delegates_to_wrapped(self):
        df = pd.DataFrame({"a": [1]})
        mock_dataset = MagicMock()

        wrapper = _ValidatingDataset(mock_dataset, CompaniesSchema, "companies")
        wrapper.save(df)

        mock_dataset.save.assert_called_once_with(df)

    def test_getattr_delegates_to_wrapped(self):
        mock_dataset = MagicMock()
        mock_dataset._filepath = "/some/path.csv"

        wrapper = _ValidatingDataset(mock_dataset, CompaniesSchema, "companies")

        assert wrapper._filepath == "/some/path.csv"

    def test_release_delegates_to_wrapped(self):
        mock_dataset = MagicMock()

        wrapper = _ValidatingDataset(mock_dataset, CompaniesSchema, "companies")
        wrapper.release()

        mock_dataset.release.assert_called_once()

    def test_exists_delegates_to_wrapped(self):
        mock_dataset = MagicMock()
        mock_dataset.exists.return_value = True

        wrapper = _ValidatingDataset(mock_dataset, CompaniesSchema, "companies")

        assert wrapper.exists() is True


# --- TestApplyDatasetValidation ---


class TestApplyDatasetValidation:
    """Tests for _apply_dataset_validation on KedroContext."""

    @staticmethod
    def _make_pipeline_mock(nodes):
        pipeline = MagicMock()
        pipeline.nodes = nodes
        return pipeline

    def test_wraps_matching_datasets(self, mocker):
        """Datasets with Pandera-annotated node inputs get wrapped."""

        def preprocess(companies: CompaniesSchema) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=preprocess,
            inputs="companies",
            outputs="preprocessed",
            name="preprocess",
        )

        pipeline = self._make_pipeline_mock([test_node])

        mocker.patch(
            "kedro.framework.project.pipelines",
            {"data_processing": pipeline},
        )

        mock_original_dataset = MagicMock()
        mock_catalog = MagicMock()
        mock_catalog._datasets = {"companies": mock_original_dataset}

        from kedro.framework.context.context import KedroContext

        context = MagicMock(spec=KedroContext)
        KedroContext._apply_dataset_validation(context, mock_catalog)

        wrapped = mock_catalog._datasets["companies"]
        assert isinstance(wrapped, _ValidatingDataset)
        assert wrapped._wrapped is mock_original_dataset
        assert wrapped._schema_class is CompaniesSchema

    def test_skips_datasets_not_in_catalog(self, mocker):
        """Datasets annotated but not in catalog are silently skipped."""

        def preprocess(companies: CompaniesSchema) -> pd.DataFrame:
            return companies

        test_node = kedro_node(
            func=preprocess,
            inputs="companies",
            outputs="preprocessed",
            name="preprocess",
        )

        pipeline = self._make_pipeline_mock([test_node])

        mocker.patch(
            "kedro.framework.project.pipelines",
            {"data_processing": pipeline},
        )

        mock_catalog = MagicMock()
        mock_catalog._datasets = {}  # companies not in catalog

        from kedro.framework.context.context import KedroContext

        context = MagicMock(spec=KedroContext)
        KedroContext._apply_dataset_validation(context, mock_catalog)

        assert mock_catalog._datasets == {}

    def test_does_not_wrap_unannotated_datasets(self, mocker):
        """Datasets without Pandera annotations are left untouched."""

        def process(data: pd.DataFrame) -> pd.DataFrame:
            return data

        test_node = kedro_node(
            func=process,
            inputs="raw_data",
            outputs="processed",
            name="process",
        )

        pipeline = self._make_pipeline_mock([test_node])

        mocker.patch(
            "kedro.framework.project.pipelines",
            {"pipeline": pipeline},
        )

        mock_original_dataset = MagicMock()
        mock_catalog = MagicMock()
        mock_catalog._datasets = {"raw_data": mock_original_dataset}

        from kedro.framework.context.context import KedroContext

        context = MagicMock(spec=KedroContext)
        KedroContext._apply_dataset_validation(context, mock_catalog)

        assert mock_catalog._datasets["raw_data"] is mock_original_dataset
