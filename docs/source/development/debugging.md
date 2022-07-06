# Debugging

## Introduction

If you're running your Kedro pipeline from the CLI or you can't/don't want to run Kedro from within your IDE debugging framework, it can be hard to debug your Kedro pipeline or nodes. This is particularly frustrating because:

* If you have long running nodes or pipelines, inserting `print` statements and running them multiple times quickly becomes time-consuming.
* Debugging nodes outside the `run` session isn't very helpful because getting access to the local scope within the `node` can be hard, especially if you're dealing with large data or memory datasets, where you need to chain a few nodes together or re-run your pipeline to produce the data for debugging purposes.

This guide provides examples on [how to instantiate a post-mortem debugging session](https://docs.python.org/3/library/pdb.html#pdb.post_mortem) with [`pdb`](https://docs.python.org/3/library/pdb.html) using [Kedro Hooks](../hooks/introduction.md) when an uncaught error occurs during a pipeline run. Note that [ipdb](https://pypi.org/project/ipdb/) could be integrated in the same manner.

For guides on how to set up debugging with IDEs, please visit the [guide for debugging in VSCode](./set_up_vscode.md#debugging) and the [guide for debugging in PyCharm](./set_up_pycharm.md#debugging).

## Debugging Node

To start a debugging session when an uncaught error is raised within your `node`, implement the `on_node_error` [Hook specification](/kedro.framework.hooks):

```python
import pdb
import sys
import traceback

from kedro.framework.hooks import hook_impl


class PDBNodeDebugHook:
    """A hook class for creating a post mortem debugging with the PDB debugger
    whenever an error is triggered within a node. The local scope from when the
    exception occured is available within this debugging session.
    """

    @hook_impl
    def on_node_error(self):
        _, _, traceback_object = sys.exc_info()

        #  Print the traceback information for debugging ease
        traceback.print_tb(traceback_object)

        # Drop you into a post mortem debugging session
        pdb.post_mortem(traceback_object)
```

You can then register this `PDBNodeDebugHook` in your project's `settings.py`:

```python
HOOKS = (PDBNodeDebugHook(),)
```

## Debugging Pipeline

To start a debugging session when an uncaught error is raised within your `pipeline`, implement the `on_pipeline_error` [Hook specification](/kedro.framework.hooks):

```python
import pdb
import sys
import traceback

from kedro.framework.hooks import hook_impl


class PDBPipelineDebugHook:
    """A hook class for creating a post mortem debugging with the PDB debugger
    whenever an error is triggered within a pipeline. The local scope from when the
    exception occured is available within this debugging session.
    """

    @hook_impl
    def on_pipeline_error(self):
        # We don't need the actual exception since it is within this stack frame
        _, _, traceback_object = sys.exc_info()

        #  Print the traceback information for debugging ease
        traceback.print_tb(traceback_object)

        # Drop you into a post mortem debugging session
        pdb.post_mortem(traceback_object)
```

You can then register this `PDBPipelineDebugHook` in your project's `settings.py`:

```python
HOOKS = (PDBPipelineDebugHook(),)
```
