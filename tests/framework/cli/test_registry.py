import pytest
from click.testing import CliRunner


@pytest.fixture
def yaml_dump_mock(mocker):
    return mocker.patch("yaml.dump", return_value="Result YAML")


@pytest.fixture
def pipelines_dict():
    pipelines = {
        "data_engineering": ["split_data_node (split_data)"],
        "data_science": [
            "train_model (train_model)",
            "predict (predict)",
            "report_accuracy (report_accuracy)",
        ],
        "data_processing": ["data_processing.split_data_node (split_data)"],
    }
    pipelines["__default__"] = pipelines["data_engineering"] + pipelines["data_science"]
    return pipelines


@pytest.mark.usefixtures("chdir_to_dummy_project")
def test_list_registered_pipelines(
    fake_project_cli, fake_metadata, yaml_dump_mock, pipelines_dict
):
    result = CliRunner().invoke(
        fake_project_cli, ["registry", "list"], obj=fake_metadata
    )

    assert not result.exit_code
    yaml_dump_mock.assert_called_once_with(sorted(pipelines_dict.keys()))


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestRegistryDescribeCommand:
    @pytest.mark.parametrize(
        "pipeline_name",
        ["data_engineering", "data_science", "data_processing", "__default__"],
    )
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
            "Error: 'missing' pipeline not found. Existing pipelines: "
            "[__default__, data_engineering, data_processing, data_science]\n"
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
