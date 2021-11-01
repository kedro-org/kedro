import pytest
from click.testing import CliRunner


@pytest.fixture
def yaml_dump_mock(mocker):
    return mocker.patch("yaml.dump", return_value="Result YAML")


@pytest.fixture
def pipelines_dict():
    pipelines = {
        "de": ["split_data (split_data)"],
        "ds": [
            "train_model (train_model)",
            "predict (predict)",
            "report_accuracy (report_accuracy)",
        ],
        "dp": ["data_processing.split_data (split_data)"],
    }
    pipelines["__default__"] = pipelines["de"] + pipelines["ds"]
    return pipelines


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
def test_list_registered_pipelines(
    fake_project_cli, fake_metadata, yaml_dump_mock, pipelines_dict
):
    result = CliRunner().invoke(
        fake_project_cli, ["registry", "list"], obj=fake_metadata
    )

    assert not result.exit_code
    yaml_dump_mock.assert_called_once_with(sorted(pipelines_dict.keys()))


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestRegistryDescribeCommand:
    @pytest.mark.parametrize("pipeline_name", ["de", "ds", "dp", "__default__"])
    def test_describe_registered_pipeline(
        self,
        fake_project_cli,
        fake_metadata,
        yaml_dump_mock,
        pipeline_name,
        pipelines_dict,
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["registry", "describe", pipeline_name],
            obj=fake_metadata,
        )

        assert not result.exit_code
        expected_dict = {"Nodes": pipelines_dict[pipeline_name]}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_registered_pipeline_not_found(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli, ["registry", "describe", "missing"], obj=fake_metadata
        )

        assert result.exit_code
        expected_output = (
            "Error: `missing` pipeline not found. Existing pipelines: "
            "[__default__, de, dp, ds]\n"
        )
        assert expected_output in result.output

    def test_describe_registered_pipeline_default(
        self,
        fake_project_cli,
        fake_metadata,
        yaml_dump_mock,
        pipelines_dict,
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["registry", "describe"],
            obj=fake_metadata,
        )

        assert not result.exit_code
        expected_dict = {"Nodes": pipelines_dict["__default__"]}
        yaml_dump_mock.assert_called_once_with(expected_dict)
