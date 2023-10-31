from __future__ import annotations

import shlex
import subprocess
from typing import Any

import psutil


def run(
    cmd: list | str, split: bool = True, print_output: bool = False, **kwargs: Any
) -> subprocess.CompletedProcess:
    """Run a shell command.

    Args:
        cmd: A command string, or a command followed by program
            arguments that will be submitted to Popen to run.

        split: Flag that splits command to provide as multiple *args
            to Popen. Default is True.

        print_output: If True will print previously captured stdout.
            Default is False.

        **kwargs: Extra options to pass to subprocess.

    Example:
    ::
        "ls"
        "ls -la"
        "chmod 754 local/file"

    Returns:
        Result with attributes args, returncode, stdout and stderr.

    """
    if isinstance(cmd, str) and split:
        cmd = shlex.split(cmd)
    result = subprocess.run(cmd, input="", capture_output=True, **kwargs)
    result.stdout = result.stdout.decode("utf-8")
    result.stderr = result.stderr.decode("utf-8")
    if print_output:
        print(result.stdout)
    return result


def check_run(cmd: list | str, print_output: bool = False) -> None:
    """
    Run cmd using subprocess.check_call (throws error if non-zero value
    returned)

    Args:
        cmd: command to be run
        print_output: whether to print output
    """
    if isinstance(cmd, str):
        split_cmd = shlex.split(cmd)
    else:
        split_cmd = cmd

    if print_output:
        subprocess.check_call(split_cmd)
    else:
        subprocess.check_call(split_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class ChildTerminatingPopen(subprocess.Popen):
    """Extend subprocess.Popen class to automatically kill child processes
    when terminated.

    Note:
        On GNU/Linux child processes are not killed automatically if the parent
        dies (so-called orphan processes)
    """

    def __init__(self, cmd: list[str], **kwargs) -> None:
        """
        Initializer pipes stderr and stdout.

        Args:
            cmd: command to be run.
            **kwargs: keyword arguments such as env and cwd

        """
        super().__init__(  # type: ignore
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
        )

    def terminate(self) -> None:
        """Terminate process and children."""
        try:
            proc = psutil.Process(self.pid)
            procs = [proc] + proc.children(recursive=True)
        except psutil.NoSuchProcess:
            pass
        else:
            for proc in reversed(procs):
                try:
                    proc.terminate()
                except psutil.NoSuchProcess:
                    pass
            alive = psutil.wait_procs(procs, timeout=3)[1]
            for proc in alive:
                proc.kill()
