# Use a Jupyter notebook for Kedro project experiments

This page explains how to use a Jupyter notebook to explore elements of a Kedro project. It shows how to use `kedro jupyter notebook` to set up a notebook that has access to the `catalog`, `context`, `pipelines` and `session` variables of the Kedro project so you can query them.

This page also explains how to use line magic to display a Kedro-Viz visualisation of your pipeline directly in your notebook.

## Example project

The example adds a notebook to experiment with the retired [`pandas-iris` starter](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris). As an alternative, you can follow the example using a different starter, such as [`spaceflights-pandas`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas) or just add a notebook to your own project.

We will assume the example project is called `iris`, but you can call it whatever you choose.

Navigate to the project directory (`cd iris`) and issue the following command in the terminal to launch Jupyter:

```bash
kedro jupyter notebook
```

You'll be asked if you want to opt into usage analytics on the first run of your new project. Once you've answered the question with `y` or `n`, your browser window will open with a Jupyter page that lists the folders in your project:

![The initial view in your browser](../meta/images/new_jupyter_browser_window.png)

You can now create a new Jupyter notebook using the **New** dropdown and selecting the **Kedro (iris)** kernel:

![Create a new Jupyter notebook with Kedro (iris) kernel](../meta/images/jupyter_new_notebook.png)

This opens a new browser tab to display the empty notebook:

![Your new Jupyter notebook with Kedro (iris) kernel](../meta/images/new_jupyter_notebook_view.png)

We recommend that you save your notebook in the `notebooks` folder of your Kedro project.

### What does `kedro jupyter notebook` do?

The `kedro jupyter notebook` command launches a notebook with a kernel that is [slightly customised](https://jupyter-client.readthedocs.io/en/stable/kernels.html#kernel-specs) but almost identical to the [default IPython kernel](https://ipython.readthedocs.io/en/stable/install/kernel_install.html).

This custom kernel automatically makes the following Kedro variables available:

* `catalog` (type `DataCatalog`): [Data Catalog](../data/data_catalog.md) instance that contains all defined datasets; this is a shortcut for `context.catalog`
* `context` (type `KedroContext`): Kedro project context that provides access to Kedro's library components
* `pipelines` (type `Dict[str, Pipeline]`): Pipelines defined in your [pipeline registry](../nodes_and_pipelines/run_a_pipeline.md#run-a-pipeline-by-name)
* `session` (type `KedroSession`): [Kedro session](../kedro_project_setup/session.md) that orchestrates a pipeline run

``` {note}
If the Kedro variables are not available within your Jupyter notebook, you could have a malformed configuration file or missing dependencies. The full error message is shown on the terminal used to launch `kedro jupyter notebook`.
```

## How to explore a Kedro project in a notebook
Here are some examples of how to work with the Kedro variables. To explore the full range of attributes and methods available, see the relevant [API documentation](/api/kedro) or use the [Python `dir` function](https://docs.python.org/3/library/functions.html#dir), for example `dir(catalog)`.

### `%run_viz` line magic

``` {note}
If you have not yet installed [Kedro-Viz](https://github.com/kedro-org/kedro-viz) for the project, run `pip install kedro-viz` in your terminal from within the project directory.
```

You can display an interactive visualisation of your pipeline directly in your notebook using the `run-viz` [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html) from within a cell:

```python
%run_viz
```

![View your project's Kedro Viz inside a notebook](../meta/images/run_viz_in_notebook.png)

### `catalog`

`catalog` can be used to explore your project's [Data Catalog](../data/data_catalog.md) using methods such as `catalog.list`, `catalog.load` and `catalog.save`.

For example, add the following to a cell in your notebook to run `catalog.list`:

```ipython
catalog.list()
```

When you run the cell:

```ipython
['example_iris_data',
 'parameters',
 'params:example_test_data_ratio',
 'params:example_num_train_iter',
 'params:example_learning_rate'
]
```
Next try the following for `catalog.load`:

```ipython
catalog.load("example_iris_data")
```

The output:

```ipython
INFO     Loading data from 'example_iris_data' (CSVDataset)...

     sepal_length  sepal_width  petal_length  petal_width    species
0             5.1          3.5           1.4          0.2     setosa
1             4.9          3.0           1.4          0.2     setosa
2             4.7          3.2           1.3          0.2     setosa
3             4.6          3.1           1.5          0.2     setosa
4             5.0          3.6           1.4          0.2     setosa
..            ...          ...           ...          ...        ...
145           6.7          3.0           5.2          2.3  virginica
146           6.3          2.5           5.0          1.9  virginica
147           6.5          3.0           5.2          2.0  virginica
148           6.2          3.4           5.4          2.3  virginica
149           5.9          3.0           5.1          1.8  virginica
```

Now try the following:

```ipython
catalog.load("parameters")
```
You should see this:

```ipython
INFO     Loading data from 'parameters' (MemoryDataset)...

{'example_test_data_ratio': 0.2,
 'example_num_train_iter': 10000,
 'example_learning_rate': 0.01}
```

```{note}
If you enable [versioning](../data/data_catalog.md#dataset-versioning) you can load a particular version of a dataset, e.g. `catalog.load("example_train_x", version="2021-12-13T15.08.09.255Z")`.
```

### `context`

`context` enables you to access Kedro's library components and project metadata. For example, if you add the following to a cell and run it:

```ipython
context.project_path
```
You should see output like this, according to your username and path:

```ipython
PosixPath('/Users/username/kedro_projects/iris')
```

You can find out more about the `context` in the [API documentation](/api/kedro.framework.context.KedroContext).

### `pipelines`

`pipelines` is a dictionary containing your project's [registered pipelines](../nodes_and_pipelines/run_a_pipeline.md#run-a-pipeline-by-name):

```ipython
pipelines
```

The output will be a listing as follows:

```ipython
{'__default__': Pipeline([
Node(split_data, ['example_iris_data', 'parameters'], ['X_train', 'X_test', 'y_train', 'y_test'], 'split'),
Node(make_predictions, ['X_train', 'X_test', 'y_train'], 'y_pred', 'make_predictions'),
Node(report_accuracy, ['y_pred', 'y_test'], None, 'report_accuracy')
])}
```

You can use this to explore your pipelines and the nodes they contain:

```ipython
pipelines["__default__"].all_outputs()
```
Should give the output:

```ipython
{'y_pred', 'X_test', 'y_train', 'X_train', 'y_test'}
```

### `session`

`session.run` allows you to run a pipeline. With no arguments, this will run your `__default__` project pipeline sequentially, much as a call to `kedro run` from the terminal:

```ipython
session.run()
```

You can also specify the following optional arguments for `session.run`:

| Argument name   | Accepted types   | Description                                                                                                                                          |
| --------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tags`          | `Iterable[str]`  | Construct the pipeline using nodes which have this tag attached. A node is included in the resulting pipeline if it contains any of those tags  |
| `runner`        | `AbstractRunner` | An instance of Kedro [AbstractRunner](/api/kedro.runner.AbstractRunner). Can be an instance of a [ParallelRunner](/api/kedro.runner.ParallelRunner)          |
| `node_names`    | `Iterable[str]`  | Run nodes with specified names                                                                                                                  |
| `from_nodes`    | `Iterable[str]`  | A list of node names which should be used as a starting point                                                                                        |
| `to_nodes`      | `Iterable[str]`  | A list of node names which should be used as an end point                                                                                            |
| `from_inputs`   | `Iterable[str]`  | A list of dataset names which should be used as a starting point                                                                                     |
| `to_outputs`    | `Iterable[str]`  | A list of dataset names which should be used as an end point                                                                                         |
| `load_versions` | `Dict[str, str]` | A mapping of a dataset name to a specific dataset version (timestamp) for loading. Applies to versioned datasets
                                |
| `pipeline_name` | `str`            | Name of the modular pipeline to run. Must be one of those returned by the `register_pipelines` function in `src/<package_name>/pipeline_registry.py` |

You can execute one *successful* run per session, as there's a one-to-one mapping between a session and a run. If you wish to do more than one run, you'll have to run `%reload_kedro` line magic to get a new `session`.

#### `%reload_kedro` line magic

You can use `%reload_kedro` [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html) within your Jupyter notebook to reload the Kedro variables (for example, if you need to update `catalog` following changes to your Data Catalog).

You don't need to restart the kernel for the `catalog`, `context`, `pipelines` and `session` variables.

`%reload_kedro` accepts optional keyword arguments `env` and `params`. For example, to use configuration environment `prod`:

```ipython
%reload_kedro --env=prod
```

For more details, run `%reload_kedro?`.


## Debugging a Kedro project within a notebook

 You can use the `%debug` [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-debug) to launch an interactive debugger in your Jupyter notebook. Declare it before a single-line statement to step through the execution in debug mode. You can use the argument `--breakpoint` or `-b` to provide a breakpoint.
The follow sequence occurs when `%debug` runs immediately after an error occurs:
 - The stack trace of the last unhandled exception loads.
 - The program stops at the point where the exception occurred.
 - An interactive shell where the user can navigate through the stack trace opens.

 You can then inspect the value of expressions and arguments, or add breakpoints to the code.

<details>
<summary>Click to see an example.</summary>

![jupyter_ipython_debug_command](../meta/images/jupyter_ipython_debug_command.gif)

</details>

---

You can set up the debugger to run automatically when an exception occurs by using the `%pdb` [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html#magic-pdb). This automatic behaviour can be enabled with `%pdb 1` or `%pdb on` before executing a program, and disabled with `%pdb 0` or `%pdb off`.

<details>
<summary>Click to see an example.</summary>

 ![jupyter_ipython_pdb_command](../meta/images/jupyter_ipython_pdb_command.gif)

</details>

---

Some examples of the possible commands that can be used to interact with the ipdb shell are as follows:

| Command           | Description                                           |
| ----------------- | ----------------------------------------------------- |
| `list`            | Show the current location in the file                 |
| `h(elp)`          | Show a list of commands, or find help on a specific command |
| `q(uit)`          | Quit the debugger and the program                     |
| `c(ontinue)`      | Quit the debugger, continue in the program             |
| `n(ext)`          | Go to the next step of the program                     |
| `<enter>`         | Repeat the previous command                            |
| `p(rint)`         | Print variables                                       |
| `s(tep)`          | Step into a subroutine                                |
| `r(eturn)`        | Return out of a subroutine                            |
| `b(reak)`         | Insert a breakpoint                                   |
| `a(rgs)`          | Print the argument list of the current function        |

For more information, use the `help` command in the debugger, or take at the [ipdb repository](https://github.com/gotcha/ipdb) for guidance.

## Useful to know (for advanced users)
Each Kedro project has its own Jupyter kernel so you can switch between Kedro projects from a single Jupyter instance by selecting the appropriate kernel.

To ensure that a Jupyter kernel always points to the correct Python executable, if one already exists with the same name `kedro_<package_name>`, then it is replaced.

You can use the `jupyter kernelspec` set of commands to manage your Jupyter kernels. For example, to remove a kernel, run `jupyter kernelspec remove <kernel_name>`.

### Managed services

If you work within a managed Jupyter service such as a Databricks notebook you may be unable to execute `kedro jupyter notebook`. You can explicitly load the Kedro IPython extension with the `%load_ext` line magic:

```ipython
In [1]: %load_ext kedro.ipython
```

If you launch your Jupyter instance from outside your Kedro project, you will need to run a second line magic to set the project path so that Kedro can load the `catalog`, `context`, `pipelines` and `session` variables:

```ipython
In [2]: %reload_kedro <project_root>
```
The Kedro IPython extension remembers the project path so that future calls to `%reload_kedro` do not need to specify it:

```ipython
In [1]: %load_ext kedro.ipython
In [2]: %reload_kedro <project_root>
In [3]: %reload_kedro
```

### IPython, JupyterLab and other Jupyter clients

You can also connect an IPython shell to a Kedro project kernel as follows:

```bash
kedro ipython
```

The command launches an IPython shell with the extension already loaded and is the same command as  `ipython --ext kedro.ipython`. You first saw this in action in the [spaceflights tutorial](../tutorial/set_up_data.md#test-that-kedro-can-load-the-data).


Similarly, the following creates a custom Jupyter kernel that automatically loads the extension and launches JupyterLab with this kernel selected:

```bash
kedro jupyter lab
```

You can use any other Jupyter client to connect to a Kedro project kernel such as the [Qt Console](https://qtconsole.readthedocs.io/), which can be launched using the `kedro_iris` kernel as follows:

```bash
jupyter qtconsole --kernel=kedro_iris
```

This will automatically load the Kedro IPython in a console that supports graphical features such as embedded figures:
![Plot of example iris data in a Qt Console](../meta/images/jupyter_qtconsole.png)
