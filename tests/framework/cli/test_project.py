import sys
from os import rename

import pytest
from click.testing import CliRunner
from omegaconf import OmegaConf

from kedro.framework.cli.utils import KedroCliError
from kedro.framework.session import KedroSession
from kedro.runner import ParallelRunner, SequentialRunner


@pytest.fixture(autouse=True)
def call_mock(mocker):
    return mocker.patch("kedro.framework.cli.project.call")


@pytest.fixture
def fake_copyfile(mocker):
    return mocker.patch("shutil.copyfile")


@pytest.fixture
def fake_session(mocker):
    mock_session = mocker.Mock()
    mock_session.run = mocker.Mock()

    mock_session_context = mocker.patch("kedro.framework.session.KedroSession.create")
    mock_session_context.return_value.__enter__.return_value = mock_session

    return mock_session


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestIpythonCommand:
    def test_happy_path(
        self,
        call_mock,
        fake_project_cli,
        fake_repo_path,
        fake_metadata,
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["ipython", "--random-arg", "value"], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        call_mock.assert_called_once_with(
            [
                "ipython",
                "--ext",
                "kedro.ipython",
                "--random-arg",
                "value",
            ]
        )

    @pytest.mark.parametrize("env_flag,env", [("--env", "base"), ("-e", "local")])
    def test_env(
        self,
        env_flag,
        env,
        fake_project_cli,
        mocker,
        fake_metadata,
    ):
        """This tests starting ipython with specific env."""
        mock_environ = mocker.patch("os.environ", {})
        result = CliRunner().invoke(
            fake_project_cli, ["ipython", env_flag, env], obj=fake_metadata
        )
        assert not result.exit_code, result.stdout
        assert mock_environ["KEDRO_ENV"] == env

    def test_fail_no_ipython(self, fake_project_cli, mocker):
        mocker.patch.dict("sys.modules", {"IPython": None})
        result = CliRunner().invoke(fake_project_cli, ["ipython"])

        assert result.exit_code
        error = (
            "Module 'IPython' not found. Make sure to install required project "
            "dependencies by running the 'pip install -r requirements.txt' command first."
        )
        assert error in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestPackageCommand:
    def test_happy_path(
        self, call_mock, fake_project_cli, mocker, fake_repo_path, fake_metadata
    ):
        result = CliRunner().invoke(fake_project_cli, ["package"], obj=fake_metadata)
        assert not result.exit_code, result.stdout
        call_mock.assert_has_calls(
            [
                mocker.call(
                    [
                        sys.executable,
                        "-m",
                        "build",
                        "--wheel",
                        "--outdir",
                        "dist",
                    ],
                    cwd=str(fake_repo_path),
                ),
                mocker.call(
                    [
                        "tar",
                        "--exclude=local/*.yml",
                        "-czf",
                        f"dist/conf-{fake_metadata.package_name}.tar.gz",
                        f"--directory={fake_metadata.project_path}",
                        "conf",
                    ],
                ),
            ]
        )

    def test_no_pyproject_toml(
        self, call_mock, fake_project_cli, mocker, fake_repo_path, fake_metadata
    ):
        # Assume no pyproject.toml
        (fake_metadata.project_path / "pyproject.toml").unlink(missing_ok=True)

        result = CliRunner().invoke(fake_project_cli, ["package"], obj=fake_metadata)
        assert not result.exit_code, result.stdout

        # destination_dir will be different since pyproject.toml doesn't exist
        call_mock.assert_has_calls(
            [
                mocker.call(
                    [
                        sys.executable,
                        "-m",
                        "build",
                        "--wheel",
                        "--outdir",
                        "../dist",
                    ],
                    cwd=str(fake_metadata.source_dir),
                ),
                mocker.call(
                    [
                        "tar",
                        "--exclude=local/*.yml",
                        "-czf",
                        f"dist/conf-{fake_metadata.package_name}.tar.gz",
                        f"--directory={fake_metadata.project_path}",
                        "conf",
                    ]
                ),
            ]
        )


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestRunCommand:
    @staticmethod
    @pytest.fixture(params=["run_config.yml", "run_config.json"])
    def fake_run_config(request, fake_root_dir):
        config_path = str(fake_root_dir / request.param)
        config = {
            "run": {
                "pipeline": "pipeline1",
                "tags": "tag1, tag2",
                "node_names": "node1, node2",
            },
            "dummy": {"dummy": "dummy"},
        }
        OmegaConf.save(
            config,
            config_path,
        )
        return config_path

    @staticmethod
    @pytest.fixture(params=["run_config.yml", "run_config.json"])
    def fake_invalid_run_config(request, fake_root_dir):
        config_path = str(fake_root_dir / request.param)
        config = {
            "run": {
                "pipeline": "pipeline1",
                "tags": "tag1, tag2",
                "node-names": "node1, node2",
            },
            "dummy": {"dummy": "dummy"},
        }
        OmegaConf.save(
            config,
            config_path,
        )
        return config_path

    @staticmethod
    @pytest.fixture
    def fake_run_config_with_params(fake_run_config, request):
        config = OmegaConf.to_container(OmegaConf.load(fake_run_config))
        config["run"].update(request.param)
        OmegaConf.save(config, fake_run_config)
        return fake_run_config

    def test_run_successfully(
        self, fake_project_cli, fake_metadata, fake_session, mocker
    ):
        result = CliRunner().invoke(fake_project_cli, ["run"], obj=fake_metadata)
        assert not result.exit_code

        fake_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=False,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    @pytest.mark.parametrize(
        "nodes_input, nodes_expected",
        [
            ["splitting_data", ("splitting_data",)],
            ["splitting_data,training_model", ("splitting_data", "training_model")],
            ["splitting_data, training_model", ("splitting_data", "training_model")],
        ],
    )
    def test_run_specific_nodes(
        self,
        fake_project_cli,
        fake_metadata,
        fake_session,
        mocker,
        nodes_input,
        nodes_expected,
    ):
        nodes_command = "--nodes=" + nodes_input
        result = CliRunner().invoke(
            fake_project_cli, ["run", nodes_command], obj=fake_metadata
        )
        assert not result.exit_code

        fake_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=nodes_expected,
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=False,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    @pytest.mark.parametrize(
        "tags_input, tags_expected",
        [
            ["tag1", ("tag1",)],
            ["tag1,tag2", ("tag1", "tag2")],
            ["tag1, tag2", ("tag1", "tag2")],
        ],
    )
    def test_run_with_tags(
        self,
        fake_project_cli,
        fake_metadata,
        fake_session,
        mocker,
        tags_input,
        tags_expected,
    ):
        tags_command = "--tags=" + tags_input
        result = CliRunner().invoke(
            fake_project_cli, ["run", tags_command], obj=fake_metadata
        )
        assert not result.exit_code

        fake_session.run.assert_called_once_with(
            tags=tags_expected,
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=False,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    def test_run_with_pipeline_filters(
        self, fake_project_cli, fake_metadata, fake_session, mocker
    ):
        from_nodes = ["--from-nodes", "splitting_data"]
        to_nodes = ["--to-nodes", "training_model"]
        namespaces = ["--namespaces", "fake_namespace"]
        tags = ["--tags", "de"]
        result = CliRunner().invoke(
            fake_project_cli,
            ["run", *from_nodes, *to_nodes, *tags, *namespaces],
            obj=fake_metadata,
        )
        assert not result.exit_code

        fake_session.run.assert_called_once_with(
            tags=("de",),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=from_nodes[1:],
            to_nodes=to_nodes[1:],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=["fake_namespace"],
            only_missing_outputs=False,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    def test_run_successfully_parallel(
        self, fake_project_cli, fake_metadata, fake_session, mocker
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--runner=ParallelRunner"], obj=fake_metadata
        )
        assert not result.exit_code
        fake_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=False,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, ParallelRunner)
        assert not runner._is_async

    def test_run_async(self, fake_project_cli, fake_metadata, fake_session):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--async"], obj=fake_metadata
        )
        assert not result.exit_code
        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert runner._is_async

    @pytest.mark.parametrize("config_flag", ["--config", "-c"])
    def test_run_with_config(
        self,
        config_flag,
        fake_project_cli,
        fake_metadata,
        fake_session,
        fake_run_config,
        mocker,
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["run", config_flag, fake_run_config], obj=fake_metadata
        )
        assert not result.exit_code
        fake_session.run.assert_called_once_with(
            tags=("tag1", "tag2"),
            runner=mocker.ANY,
            node_names=("node1", "node2"),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name="pipeline1",
            namespaces=[],
            only_missing_outputs=False,
        )

    @pytest.mark.parametrize("config_flag", ["--config", "-c"])
    def test_run_with_invalid_config(
        self,
        config_flag,
        fake_project_cli,
        fake_metadata,
        fake_session,
        fake_invalid_run_config,
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["run", config_flag, fake_invalid_run_config],
            obj=fake_metadata,
        )
        assert result.exit_code
        assert (
            "Key `node-names` in provided configuration is not valid. \n\nDid you mean one of "
            "these?\n    node_names\n    to_nodes\n    namespaces" in result.stdout
        )
        KedroCliError.VERBOSE_EXISTS = True

    @pytest.mark.parametrize(
        "fake_run_config_with_params,expected",
        [
            ({}, {}),
            ({"params": {"foo": "baz"}}, {"foo": "baz"}),
            ({"params": "foo=baz"}, {"foo": "baz"}),
            (
                {"params": {"foo": "123.45", "baz": "678", "bar": 9}},
                {"foo": "123.45", "baz": "678", "bar": 9},
            ),
        ],
        indirect=["fake_run_config_with_params"],
    )
    def test_run_with_params_in_config(
        self,
        expected,
        fake_project_cli,
        fake_metadata,
        fake_run_config_with_params,
        mocker,
    ):
        mock_session_create = mocker.patch.object(KedroSession, "create")
        mocked_session = mock_session_create.return_value.__enter__.return_value

        result = CliRunner().invoke(
            fake_project_cli,
            ["run", "-c", fake_run_config_with_params],
            obj=fake_metadata,
        )

        assert not result.exit_code
        mocked_session.run.assert_called_once_with(
            tags=("tag1", "tag2"),
            runner=mocker.ANY,
            node_names=("node1", "node2"),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name="pipeline1",
            namespaces=[],
            only_missing_outputs=False,
        )
        mock_session_create.assert_called_once_with(
            env=mocker.ANY, conf_source=None, runtime_params=expected
        )

    @pytest.mark.parametrize(
        "cli_arg,expected_runtime_params",
        [
            ("foo=bar", {"foo": "bar"}),
            (
                "foo=123.45, bar=1a,baz=678. ,qux=1e-2,quux=0,quuz=",
                {
                    "foo": 123.45,
                    "bar": "1a",
                    "baz": 678.0,
                    "qux": 0.01,
                    "quux": 0,
                    "quuz": None,
                },
            ),
            ("foo=bar,baz=fizz=buzz", {"foo": "bar", "baz": "fizz=buzz"}),
            ("foo=fizz=buzz", {"foo": "fizz=buzz"}),
            (
                "foo=bar, baz= https://example.com",
                {"foo": "bar", "baz": "https://example.com"},
            ),
            ("foo=bar, foo=fizz buzz", {"foo": "fizz buzz"}),
            ("foo=bar,baz=fizz buzz", {"foo": "bar", "baz": "fizz buzz"}),
            ("foo.nested=bar", {"foo": {"nested": "bar"}}),
            ("foo.nested=123.45", {"foo": {"nested": 123.45}}),
            (
                "foo.nested_1.double_nest=123.45,foo.nested_2=1a",
                {"foo": {"nested_1": {"double_nest": 123.45}, "nested_2": "1a"}},
            ),
        ],
    )
    def test_run_runtime_params(
        self,
        mocker,
        fake_project_cli,
        fake_metadata,
        cli_arg,
        expected_runtime_params,
    ):
        mock_session_create = mocker.patch.object(KedroSession, "create")

        result = CliRunner().invoke(
            fake_project_cli, ["run", "--params", cli_arg], obj=fake_metadata
        )

        assert not result.exit_code
        mock_session_create.assert_called_once_with(
            env=mocker.ANY, conf_source=None, runtime_params=expected_runtime_params
        )

    @pytest.mark.parametrize("bad_arg", ["bad", "foo=bar,bad"])
    def test_bad_runtime_params(self, fake_project_cli, fake_metadata, bad_arg):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--params", bad_arg], obj=fake_metadata
        )
        assert result.exit_code
        assert (
            "Item `bad` must contain a key and a value separated by `=`."
            in result.stdout
        )

    @pytest.mark.parametrize("bad_arg", ["=", "=value", " =value"])
    def test_bad_params_key(self, fake_project_cli, fake_metadata, bad_arg):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--params", bad_arg], obj=fake_metadata
        )
        assert result.exit_code
        assert "Parameter key cannot be an empty string" in result.stdout

    @pytest.mark.parametrize(
        "lv_input, lv_dict",
        [
            [
                "dataset1:time1",
                {
                    "dataset1": "time1",
                },
            ],
            [
                "dataset1:time1,dataset2:time2",
                {"dataset1": "time1", "dataset2": "time2"},
            ],
            [
                "dataset1:time1, dataset2:time2",
                {"dataset1": "time1", "dataset2": "time2"},
            ],
        ],
    )
    def test_split_load_versions(
        self, fake_project_cli, fake_metadata, fake_session, lv_input, lv_dict, mocker
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--load-versions", lv_input], obj=fake_metadata
        )
        assert not result.exit_code, result.output

        fake_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions=lv_dict,
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=False,
        )

    def test_fail_split_load_versions(self, fake_project_cli, fake_metadata):
        load_version = "2020-05-12T12.00.00"
        result = CliRunner().invoke(
            fake_project_cli,
            ["run", "--load-versions", load_version],
            obj=fake_metadata,
        )
        assert result.exit_code, result.output

        expected_output = (
            f"Error: Expected the form of 'load_versions' to be "
            f"'dataset_name:YYYY-MM-DDThh.mm.ss.sssZ',"
            f"found {load_version} instead\n"
        )
        assert expected_output in result.output

    @pytest.mark.parametrize(
        "from_nodes, expected",
        [
            (["--from-nodes", "A,B,C"], ["A", "B", "C"]),
            (
                ["--from-nodes", "two_inputs([A0,B0]) -> [C1]"],
                ["two_inputs([A0,B0]) -> [C1]"],
            ),
            (
                ["--from-nodes", "two_outputs([A0]) -> [B1,C1]"],
                ["two_outputs([A0]) -> [B1,C1]"],
            ),
            (
                ["--from-nodes", "multi_in_out([A0,B0]) -> [C1,D1]"],
                ["multi_in_out([A0,B0]) -> [C1,D1]"],
            ),
            (
                ["--from-nodes", "two_inputs([A0,B0]) -> [C1],X,Y,Z"],
                ["two_inputs([A0,B0]) -> [C1]", "X", "Y", "Z"],
            ),
        ],
    )
    def test_safe_split_option_arguments(
        self,
        fake_project_cli,
        fake_metadata,
        fake_session,
        mocker,
        from_nodes,
        expected,
    ):
        CliRunner().invoke(fake_project_cli, ["run", *from_nodes], obj=fake_metadata)

        fake_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=expected,
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=False,
        )

    def test_run_with_alternative_conf_source(self, fake_project_cli, fake_metadata):
        # check that Kedro runs successfully with an alternative conf_source
        rename("conf", "alternate_conf")
        result = CliRunner().invoke(
            fake_project_cli,
            ["run", "--conf-source", "alternate_conf"],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

    def test_run_with_non_existent_conf_source(self, fake_project_cli, fake_metadata):
        # check that an error is thrown if target conf_source doesn't exist
        result = CliRunner().invoke(
            fake_project_cli,
            ["run", "--conf-source", "nonexistent_dir"],
            obj=fake_metadata,
        )
        assert result.exit_code, result.output
        expected_output = (
            "Error: Invalid value for '--conf-source': Path 'nonexistent_dir'"
            " does not exist."
        )
        assert expected_output in result.output

    def test_run_with_only_missing_outputs(
        self, fake_project_cli, fake_metadata, fake_session, mocker
    ):
        """Test running with --only-missing-outputs flag"""
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--only-missing-outputs"], obj=fake_metadata
        )
        assert not result.exit_code

        fake_session.run.assert_called_once_with(
            tags=(),
            runner=mocker.ANY,
            node_names=(),
            from_nodes=[],
            to_nodes=[],
            from_inputs=[],
            to_outputs=[],
            load_versions={},
            pipeline_name=None,
            namespaces=[],
            only_missing_outputs=True,
        )
