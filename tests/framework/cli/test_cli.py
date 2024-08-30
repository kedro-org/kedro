from collections import namedtuple
from itertools import cycle
from os import rename
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner
from omegaconf import OmegaConf
from pytest import fixture, mark, raises, warns

from kedro import KedroDeprecationWarning
from kedro import __version__ as version
from kedro.framework.cli import load_entry_points
from kedro.framework.cli.cli import (
    KedroCLI,
    _init_plugins,
    cli,
    global_commands,
    project_commands,
)
from kedro.framework.cli.utils import (
    CommandCollection,
    KedroCliError,
    _clean_pycache,
    find_run_command,
    forward_command,
    get_pkg_version,
)
from kedro.framework.session import KedroSession
from kedro.runner import ParallelRunner, SequentialRunner


@click.group(name="stub_cli")
def stub_cli():
    """Stub CLI group description."""
    print("group callback")


@stub_cli.command(name="stub_command")
def stub_command():
    print("command callback")


@forward_command(stub_cli, name="forwarded_command")
def forwarded_command(args, **kwargs):
    print("fred", args)


@forward_command(stub_cli, name="forwarded_help", forward_help=True)
def forwarded_help(args, **kwargs):
    print("fred", args)


@forward_command(stub_cli)
def unnamed(args, **kwargs):
    print("fred", args)


@fixture
def requirements_file(tmp_path):
    body = "\n".join(["SQLAlchemy>=1.2.0, <2.0", "pandas==0.23.0", "toposort"]) + "\n"
    reqs_file = tmp_path / "requirements.txt"
    reqs_file.write_text(body)
    yield reqs_file


@fixture
def fake_session(mocker):
    mock_session_create = mocker.patch.object(KedroSession, "create")
    mocked_session = mock_session_create.return_value.__enter__.return_value
    return mocked_session


class TestCliCommands:
    def test_cli(self):
        """Run `kedro` without arguments."""
        result = CliRunner().invoke(cli, [])

        assert result.exit_code == 0
        assert "kedro" in result.output

    def test_print_version(self):
        """Check that `kedro --version` and `kedro -V` outputs contain
        the current package version."""
        result = CliRunner().invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert version in result.output

        result_abr = CliRunner().invoke(cli, ["-V"])
        assert result_abr.exit_code == 0
        assert version in result_abr.output

    def test_info_contains_plugin_versions(self, entry_point):
        entry_point.dist.version = "1.0.2"
        entry_point.module = "bob.fred"

        result = CliRunner().invoke(cli, ["info"])
        assert result.exit_code == 0
        assert (
            "bob: 1.0.2 (entry points:cli_hooks,global,hooks,init,line_magic,project,starters)"
            in result.output
        )

        entry_point.load.assert_not_called()

    def test_info_only_kedro_telemetry_plugin_installed(self):
        result = CliRunner().invoke(cli, ["info"])
        assert result.exit_code == 0

        split_result = result.output.strip().split("\n")
        assert "Installed plugins" in split_result[-2]
        assert "kedro_telemetry" in split_result[-1]

    def test_help(self):
        """Check that `kedro --help` returns a valid help message."""
        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "kedro" in result.output

        result = CliRunner().invoke(cli, ["-h"])
        assert result.exit_code == 0
        assert "-h, --help     Show this message and exit." in result.output


class TestCommandCollection:
    def test_found(self):
        """Test calling existing command."""
        cmd_collection = CommandCollection(("Commands", [cli, stub_cli]))
        result = CliRunner().invoke(cmd_collection, ["stub_command"])
        assert result.exit_code == 0
        assert "group callback" not in result.output
        assert "command callback" in result.output

    def test_found_reverse(self):
        """Test calling existing command."""
        cmd_collection = CommandCollection(("Commands", [stub_cli, cli]))
        result = CliRunner().invoke(cmd_collection, ["stub_command"])
        assert result.exit_code == 0
        assert "group callback" in result.output
        assert "command callback" in result.output

    def test_not_found(self):
        """Test calling nonexistent command."""
        cmd_collection = CommandCollection(("Commands", [cli, stub_cli]))
        result = CliRunner().invoke(cmd_collection, ["not_found"])
        assert result.exit_code == 2
        assert "No such command" in result.output
        assert "Did you mean one of these" not in result.output

    def test_not_found_closest_match(self, mocker):
        """Check that calling a nonexistent command with a close match returns the close match"""
        patched_difflib = mocker.patch(
            "kedro.framework.cli.utils.difflib.get_close_matches",
            return_value=["suggestion_1", "suggestion_2"],
        )

        cmd_collection = CommandCollection(("Commands", [cli, stub_cli]))
        result = CliRunner().invoke(cmd_collection, ["not_found"])

        patched_difflib.assert_called_once_with(
            "not_found", mocker.ANY, mocker.ANY, mocker.ANY
        )

        assert result.exit_code == 2
        assert "No such command" in result.output
        assert "Did you mean one of these?" in result.output
        assert "suggestion_1" in result.output
        assert "suggestion_2" in result.output

    def test_not_found_closet_match_singular(self, mocker):
        """Check that calling a nonexistent command with a close match has the proper wording"""
        patched_difflib = mocker.patch(
            "kedro.framework.cli.utils.difflib.get_close_matches",
            return_value=["suggestion_1"],
        )

        cmd_collection = CommandCollection(("Commands", [cli, stub_cli]))
        result = CliRunner().invoke(cmd_collection, ["not_found"])

        patched_difflib.assert_called_once_with(
            "not_found", mocker.ANY, mocker.ANY, mocker.ANY
        )

        assert result.exit_code == 2
        assert "No such command" in result.output
        assert "Did you mean this?" in result.output
        assert "suggestion_1" in result.output

    def test_help(self):
        """Check that help output includes stub_cli group description."""
        cmd_collection = CommandCollection(("Commands", [cli, stub_cli]))
        result = CliRunner().invoke(cmd_collection, [])
        assert result.exit_code == 0
        assert "Stub CLI group description" in result.output
        assert "Kedro is a CLI" in result.output


class TestForwardCommand:
    def test_regular(self):
        """Test forwarded command invocation."""
        result = CliRunner().invoke(stub_cli, ["forwarded_command", "bob"])
        assert result.exit_code == 0, result.output
        assert "bob" in result.output
        assert "fred" in result.output
        assert "--help" not in result.output
        assert "forwarded_command" not in result.output

    def test_unnamed(self):
        """Test forwarded command invocation."""
        result = CliRunner().invoke(stub_cli, ["unnamed", "bob"])
        assert result.exit_code == 0, result.output
        assert "bob" in result.output
        assert "fred" in result.output
        assert "--help" not in result.output
        assert "forwarded_command" not in result.output

    def test_help(self):
        """Test help output for the command with help flags not forwarded."""
        result = CliRunner().invoke(stub_cli, ["forwarded_command", "bob", "--help"])
        assert result.exit_code == 0, result.output
        assert "bob" not in result.output
        assert "fred" not in result.output
        assert "--help" in result.output
        assert "forwarded_command" in result.output

    def test_forwarded_help(self):
        """Test help output for the command with forwarded help flags."""
        result = CliRunner().invoke(stub_cli, ["forwarded_help", "bob", "--help"])
        assert result.exit_code == 0, result.output
        assert "bob" in result.output
        assert "fred" in result.output
        assert "--help" in result.output
        assert "forwarded_help" not in result.output


class TestCliUtils:
    def test_get_pkg_version(self, requirements_file):
        """Test get_pkg_version(), which extracts package version
        from the provided requirements file."""
        sa_version = "SQLAlchemy>=1.2.0, <2.0"
        assert get_pkg_version(requirements_file, "SQLAlchemy") == sa_version
        assert get_pkg_version(requirements_file, "pandas") == "pandas==0.23.0"
        assert get_pkg_version(requirements_file, "toposort") == "toposort"
        with raises(KedroCliError):
            get_pkg_version(requirements_file, "nonexistent")
        with raises(KedroCliError):
            non_existent_file = str(requirements_file) + "-nonexistent"
            get_pkg_version(non_existent_file, "pandas")

    def test_get_pkg_version_deprecated(self, requirements_file):
        with warns(
            KedroDeprecationWarning,
            match=r"\`get_pkg_version\(\)\` has been deprecated",
        ):
            _ = get_pkg_version(requirements_file, "pandas")

    def test_clean_pycache(self, tmp_path, mocker):
        """Test `clean_pycache` utility function"""
        source = Path(tmp_path)
        pycache2 = Path(source / "nested1" / "nested2" / "__pycache__").resolve()
        pycache2.mkdir(parents=True)
        pycache1 = Path(source / "nested1" / "__pycache__").resolve()
        pycache1.mkdir()
        pycache = Path(source / "__pycache__").resolve()
        pycache.mkdir()

        mocked_rmtree = mocker.patch("shutil.rmtree")
        _clean_pycache(source)

        expected_calls = [
            mocker.call(pycache, ignore_errors=True),
            mocker.call(pycache1, ignore_errors=True),
            mocker.call(pycache2, ignore_errors=True),
        ]
        assert mocked_rmtree.mock_calls == expected_calls

    def test_find_run_command_non_existing_project(self):
        with pytest.raises(ModuleNotFoundError, match="No module named 'fake_project'"):
            _ = find_run_command("fake_project")

    def test_find_run_command_with_clipy(
        self, fake_metadata, fake_repo_path, fake_project_cli, mocker
    ):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )

        mock_project_cli = MagicMock(spec=[fake_repo_path / "cli.py"])
        mock_project_cli.cli = MagicMock(spec=["cli"])
        mock_project_cli.run = MagicMock(spec=["run"])
        mocker.patch(
            "kedro.framework.cli.utils.importlib.import_module",
            return_value=mock_project_cli,
        )

        run = find_run_command(fake_metadata.package_name)
        assert run is mock_project_cli.run

    def test_find_run_command_no_clipy(self, fake_metadata, fake_repo_path, mocker):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        mock_project_cli = MagicMock(spec=[fake_repo_path / "cli.py"])
        mocker.patch(
            "kedro.framework.cli.utils.importlib.import_module",
            return_value=mock_project_cli,
        )

        with raises(KedroCliError, match="Cannot load commands from"):
            _ = find_run_command(fake_metadata.package_name)

    def test_find_run_command_use_plugin_run(
        self, fake_metadata, fake_repo_path, mocker
    ):
        mock_plugin = MagicMock(spec=["plugins"])
        mock_command = MagicMock(name="run_command")
        mock_plugin.commands = {"run": mock_command}
        mocker.patch(
            "kedro.framework.cli.utils.load_entry_points", return_value=[mock_plugin]
        )

        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module",
            side_effect=ModuleNotFoundError("dummy_package.cli"),
        )

        run = find_run_command(fake_metadata.package_name)
        assert run == mock_command

    def test_find_run_command_use_default_run(self, fake_metadata, mocker):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module",
            side_effect=ModuleNotFoundError("dummy_package.cli"),
        )
        run = find_run_command(fake_metadata.package_name)
        assert run.help == "Run the pipeline."


class TestEntryPoints:
    def test_project_groups(self, entry_points, entry_point):
        entry_point.load.return_value = "groups"
        groups = load_entry_points("project")
        assert groups == ["groups"]
        entry_points.return_value.select.assert_called_once_with(
            group="kedro.project_commands"
        )

    def test_project_error_is_caught(self, entry_points, entry_point, caplog):
        entry_point.load.side_effect = Exception()
        entry_point.module = "project"
        load_entry_points("project")
        assert "Failed to load project commands" in caplog.text
        entry_points.return_value.select.assert_called_once_with(
            group="kedro.project_commands"
        )

    def test_global_groups(self, entry_points, entry_point):
        entry_point.load.return_value = "groups"
        groups = load_entry_points("global")
        assert groups == ["groups"]
        entry_points.return_value.select.assert_called_once_with(
            group="kedro.global_commands"
        )

    def test_global_error_is_caught(self, entry_points, entry_point, caplog):
        entry_point.load.side_effect = Exception()
        entry_point.module = "global"
        load_entry_points("global")
        assert "Failed to load global commands" in caplog.text
        entry_points.return_value.select.assert_called_once_with(
            group="kedro.global_commands"
        )

    def test_init(self, entry_points, entry_point):
        _init_plugins()
        entry_points.return_value.select.assert_called_once_with(group="kedro.init")
        entry_point.load().assert_called_once_with()

    def test_init_error_is_caught(self, entry_points, entry_point):
        entry_point.load.return_value.side_effect = Exception()
        with raises(Exception):
            _init_plugins()
        entry_points.return_value.select.assert_called_once_with(group="kedro.init")


class TestKedroCLI:
    def test_project_commands_no_clipy(self, mocker, fake_metadata):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module",
            side_effect=cycle([ModuleNotFoundError()]),
        )
        kedro_cli = KedroCLI(fake_metadata.project_path)
        # There is only one `LazyGroup` for project commands
        assert len(kedro_cli.project_groups) == 1
        assert kedro_cli.project_groups == [project_commands]
        # Assert that the lazy commands are listed properly
        assert kedro_cli.project_groups[0].list_commands(None) == [
            "catalog",
            "ipython",
            "jupyter",
            "micropkg",
            "package",
            "pipeline",
            "registry",
            "run",
        ]

    def test_project_commands_no_project(self, mocker, tmp_path):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=False)
        kedro_cli = KedroCLI(tmp_path)
        assert len(kedro_cli.project_groups) == 0
        assert kedro_cli._metadata is None

    def test_project_commands_invalid_clipy(self, mocker, fake_metadata):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module", return_value=None
        )
        with raises(KedroCliError, match="Cannot load commands from"):
            _ = KedroCLI(fake_metadata.project_path)

    def test_project_commands_valid_clipy(self, mocker, fake_metadata):
        Module = namedtuple("Module", ["cli"])
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        mocker.patch(
            "kedro.framework.cli.cli.importlib.import_module",
            return_value=Module(cli=cli),
        )
        kedro_cli = KedroCLI(fake_metadata.project_path)
        # The project group will now have two groups, the first from the project's cli.py and
        # the second is the lazy project command group
        assert len(kedro_cli.project_groups) == 2
        assert kedro_cli.project_groups == [
            cli,
            project_commands,
        ]

    def test_kedro_cli_no_project(self, mocker, tmp_path):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=False)
        kedro_cli = KedroCLI(tmp_path)
        assert len(kedro_cli.global_groups) == 2
        # The global groups will be the cli(group for info command) and the global commands (starter and new)
        assert kedro_cli.global_groups == [cli, global_commands]

        result = CliRunner().invoke(kedro_cli, [])

        assert result.exit_code == 0
        assert "Global commands from Kedro" in result.output
        assert "Project specific commands from Kedro" not in result.output

    def test_kedro_run_no_project(self, mocker, tmp_path):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=False)
        kedro_cli = KedroCLI(tmp_path)

        result = CliRunner().invoke(kedro_cli, ["run"])
        assert (
            "Kedro project not found in this directory. Project specific commands such as 'run' or "
            "'jupyter' are only available within a project directory." in result.output
        )

        assert (
            "Hint: Kedro is looking for a file called 'pyproject.toml, is one present in"
            " your current working directory?" in result.output
        )

    def test_kedro_cli_with_project(self, mocker, fake_metadata):
        mocker.patch("kedro.framework.cli.cli._is_project", return_value=True)
        mocker.patch(
            "kedro.framework.cli.cli.bootstrap_project", return_value=fake_metadata
        )
        kedro_cli = KedroCLI(fake_metadata.project_path)

        assert len(kedro_cli.global_groups) == 2
        assert kedro_cli.global_groups == [cli, global_commands]
        assert len(kedro_cli.project_groups) == 1
        assert kedro_cli.project_groups == [
            project_commands,
        ]

        result = CliRunner().invoke(kedro_cli, [])
        assert result.exit_code == 0
        assert "Global commands from Kedro" in result.output
        assert "Project specific commands from Kedro" in result.output

    def test_main_hook_exception_handling(self, fake_metadata):
        kedro_cli = KedroCLI(fake_metadata.project_path)
        kedro_cli._cli_hook_manager.hook.after_command_run = MagicMock()

        with patch.object(
            click.CommandCollection, "main", side_effect=Exception("Test Exception")
        ):
            result = CliRunner().invoke(kedro_cli, [])

        kedro_cli._cli_hook_manager.hook.after_command_run.assert_called_once_with(
            project_metadata=kedro_cli._metadata, command_args=[], exit_code=1
        )

        assert result.exit_code == 1


@mark.usefixtures("chdir_to_dummy_project")
class TestRunCommand:
    @staticmethod
    @fixture(params=["run_config.yml", "run_config.json"])
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
    @fixture(params=["run_config.yml", "run_config.json"])
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
    @fixture
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
            namespace=None,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    @mark.parametrize(
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
            namespace=None,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    @mark.parametrize(
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
            namespace=None,
        )

        runner = fake_session.run.call_args_list[0][1]["runner"]
        assert isinstance(runner, SequentialRunner)
        assert not runner._is_async

    def test_run_with_pipeline_filters(
        self, fake_project_cli, fake_metadata, fake_session, mocker
    ):
        from_nodes = ["--from-nodes", "splitting_data"]
        to_nodes = ["--to-nodes", "training_model"]
        namespace = ["--namespace", "fake_namespace"]
        tags = ["--tags", "de"]
        result = CliRunner().invoke(
            fake_project_cli,
            ["run", *from_nodes, *to_nodes, *tags, *namespace],
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
            namespace="fake_namespace",
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
            namespace=None,
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

    @mark.parametrize("config_flag", ["--config", "-c"])
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
            namespace=None,
        )

    @mark.parametrize("config_flag", ["--config", "-c"])
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
            "these?\n    node_names\n    to_nodes\n    namespace" in result.stdout
        )
        KedroCliError.VERBOSE_EXISTS = True

    @mark.parametrize(
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
            namespace=None,
        )
        mock_session_create.assert_called_once_with(
            env=mocker.ANY, conf_source=None, extra_params=expected
        )

    @mark.parametrize(
        "cli_arg,expected_extra_params",
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
    def test_run_extra_params(
        self,
        mocker,
        fake_project_cli,
        fake_metadata,
        cli_arg,
        expected_extra_params,
    ):
        mock_session_create = mocker.patch.object(KedroSession, "create")

        result = CliRunner().invoke(
            fake_project_cli, ["run", "--params", cli_arg], obj=fake_metadata
        )

        assert not result.exit_code
        mock_session_create.assert_called_once_with(
            env=mocker.ANY, conf_source=None, extra_params=expected_extra_params
        )

    @mark.parametrize("bad_arg", ["bad", "foo=bar,bad"])
    def test_bad_extra_params(self, fake_project_cli, fake_metadata, bad_arg):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--params", bad_arg], obj=fake_metadata
        )
        assert result.exit_code
        assert (
            "Item `bad` must contain a key and a value separated by `=`."
            in result.stdout
        )

    @mark.parametrize("bad_arg", ["=", "=value", " =value"])
    def test_bad_params_key(self, fake_project_cli, fake_metadata, bad_arg):
        result = CliRunner().invoke(
            fake_project_cli, ["run", "--params", bad_arg], obj=fake_metadata
        )
        assert result.exit_code
        assert "Parameter key cannot be an empty string" in result.stdout

    @mark.parametrize(
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
            namespace=None,
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

    @mark.parametrize(
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
            namespace=None,
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
