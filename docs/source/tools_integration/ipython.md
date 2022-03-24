# Use Kedro with IPython and Jupyter
<!--
# TODO:
# document line_magic entry point
# more info on what kernel is and that it's user level
# remove kernel
# bit on juptyer console/qtconsole
-->

This page follows the [Iris dataset example](../get_started/example_project.md) and demonstrates how to use Kedro with IPython, Jupyter Notebook and JupyterLab. We also recommend [a video by Data Engineer One](https://www.youtube.com/watch?v=dRnCovp1GRQ&t=50s&ab_channel=DataEngineerOne) that explains the transition from the use of vanilla Jupyter notebooks to Kedro.

<iframe width="560" height="315" style="max-width: 100%" src="https://www.youtube.com/embed/dRnCovp1GRQ" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

## Why use a notebook?
There are reasons why you may want to use a notebook, although in general, the principles behind Kedro would discourage their use because they have some [drawbacks when used to create production or reproducible code](https://towardsdatascience.com/5-reasons-why-you-should-switch-from-jupyter-notebook-to-scripts-cb3535ba9c95). However, there are occasions when you'd want to put some code into a notebook, for example:

* To conduct exploratory data analysis
* For experimentation as you create new Python functions (that could become Kedro nodes)
* As a tool for reporting and presentations

## Kedro IPython extension

The best way to interact with Kedro in IPython and Jupyter is through the Kedro [IPython extension](https://ipython.readthedocs.io/en/stable/config/extensions/index.html), `kedro.extras.extensions.ipython`. This launches a [Kedro session](../kedro_project_setup/session.md) and makes available the useful Kedro variables `context`, `session`, `catalog` and `pipelines`. It also provides the `%reload_kedro` line magic that is useful for reloading these variables (for example, if you change entries in your Data Catalog).

The simplest way to make use of the Kedro IPython extension is through the following commands:
* `kedro ipython`. This launches an IPython shell with the extension already loaded and is equivalent to the command `ipython --ext kedro.extras.extensions.ipython`.
* `kedro jupyter notebook`. This creates a custom Jupyter kernel that automatically loads the extension and launches Jupyter Notebook with this kernel selected.
* `kedro jupyter lab`. This creates a custom Jupyter kernel that automatically loads the extension and launches JupyterLab with this kernel selected.

Running any of the above from within your Kedro project will make the `context`, `session`, `catalog` and `pipelines` variables immediately accessible to you. 

If the above commands are not available to you (e.g. if you are working on a managed Jupyter service such as a Databricks notebook) then equivalent behaviour can be achieved by explicitly loading the Kedro IPython extension using the `%load_ext` line magic:
```ipython
In [1]: %load_ext kedro.extras.extensions.ipython
```

If your IPython or Jupyter instance was launched from outside your Kedro project then you will need to run a second line magic to set the project path so that Kedro can load the `context`, `session`, `catalog` and `pipelines` variables:
```ipython
In [2]: %reload_kedro <path_to_project_root>
```
The Kedro IPython extension remembers the project path so that subsequent calls to `%reload_kedro` do not need to specify it:

```ipython
In [1]: %load_ext kedro.extras.extensions.ipython
In [2]: %reload_kedro <path_to_project_root>
In [3]: %reload_kedro
```

```eval_rst
    .. note:: Note that if you want to pass arguments to the `reload_kedro` line magic, you should call it like a normal Python function (e.g `reload_kedro(env=env, extra_params=extra_params)` rather than using `%reload_kedro` in a notebook cell (e.g. `%reload_kedro(extra_params=extra_params)` wouldn’t work). You might have to call `%automagic False` beforehand to make this work.
```

## Kedro and IPython

You may want to use a Python kernel inside a Jupyter notebook (formerly known as IPython) to experiment with your Kedro code.

To start a standalone IPython session, run the following command in the root directory of your Kedro project:

```bash
kedro ipython
```
This opens an iPython session in your shell, which you can terminate, when you have finished, by typing:

```python
exit()
```
### Load `DataCatalog` in IPython

To test the IPython session, load the [Iris test example](https://www.kaggle.com/uciml/iris) data inside the IPython console as follows:

```python
catalog.load("example_iris_data").head()
```
You should see the following in your shell:

```bash
kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVDataSet)...

   sepal_length  sepal_width  petal_length  petal_width species
0           5.1          3.5           1.4          0.2  setosa
1           4.9          3.0           1.4          0.2  setosa
2           4.7          3.2           1.3          0.2  setosa
3           4.6          3.1           1.5          0.2  setosa
4           5.0          3.6           1.4          0.2  setosa
```


#### Dataset versioning

If you enable [versioning](../data/data_catalog.md#versioning-datasets-and-ml-models), you can load a particular version of a dataset. Given a catalog entry:

```yaml
example_train_x:
  type: pandas.CSVDataSet
  filepath: data/02_intermediate/example_train_x.csv
  versioned: true
```

and having run your pipeline at least once, you may specify which version to load:

```python
catalog.load("example_train_x", version="2019-12-13T15.08.09.255Z")
```

## Kedro and Jupyter

You may want to use Jupyter notebooks to experiment with your code as you develop new nodes for a pipeline, although you can write them as regular Python functions without a notebook. To use Kedro's Jupyter session:

```bash
kedro jupyter notebook
```

This starts a Jupyter server and opens a window in your default browser.

```eval_rst
.. note::  If you want Jupyter to listen to a different port number, then run ``kedro jupyter notebook --port <port>``.
```

Navigate to the `notebooks` folder of your Kedro project and create a new notebook.

![](../meta/images/jupyter_create_new_notebook.png)

```eval_rst
.. note::  The only kernel available by default has a name of the current project. If you need to access all available kernels, add ``--all-kernels`` to the command above.
```

Every time you start or restart a Jupyter or IPython session in the CLI using a `kedro` command, a startup script in `.ipython/profile_default/startup/00-kedro-init.py` is executed. It adds the following variables in scope:

* `catalog` (`DataCatalog`) - Data catalog instance that contains all defined datasets; this is a shortcut for `context.catalog`, but it's only created at startup time, whereas `context.catalog` is rebuilt everytime.
* `context` (`KedroContext`) - Kedro project context that provides access to Kedro's library components.
* `session` (`KedroSession`) - Kedro session that orchestrates the run
* `startup_error` (`Exception`) - An error that was raised during the execution of the startup script or `None` if no errors occurred

## How to use `context`

The `context` variable allows you to interact with Kedro library components from within the Kedro Jupyter notebook.

![context input graphic](../meta/images/jupyter_notebook_showing_context.png)

With `context`, you can access the following variables and methods:

- `context.project_path` (`Path`) - Root directory of the project
- `context.catalog` (`DataCatalog`) - An instance of [DataCatalog](/kedro.io.DataCatalog)

### Run the pipeline

If you wish to run the whole main pipeline within a notebook cell, you can do so by running:

```python
session.run()
```

The command runs the nodes from your default project pipeline in a sequential manner.

To parameterise your pipeline run, refer to [a later section on this page on run parameters](#additional-parameters-for-session-run) which lists all available options.

```eval_rst
.. note::  You can only execute one _successful_ run per session, as there's a one-to-one mapping between a session and a run. If you wish to do multiple runs, you'll have to run `%reload_kedro` to obtain a new `KedroSession` object.
```


### Parameters

The `context` object exposes the `params` property, which allows you to access all project parameters:

```python
parameters = context.params  # type: Dict
parameters["example_test_data_ratio"]
# returns the value of 'example_test_data_ratio' key from 'conf/base/parameters.yml'
```

```eval_rst
.. note::  You need to reload Kedro variables by calling `%reload_kedro` and re-run the code snippet above if you change the contents of ``parameters.yml``.
```

### Load/Save `DataCatalog` in Jupyter

You can load a dataset defined in your `conf/base/catalog.yml`:

```python
df = catalog.load("example_iris_data")
df.head()
```

![load the catalog and output head graphic](../meta/images/jupyter_notebook_workflow_loading_data.png)

The save operation in the example below is analogous to the load.

Put the following dataset entry in `conf/base/catalog.yml`:

```yaml
my_dataset:
  type: pandas.JSONDataSet
  filepath: data/01_raw/my_dataset.json
```

Next, you need to reload Kedro variables by calling `%reload_kedro` line magic in your Jupyter notebook.

Finally, you can save the data by executing the following command:

```python
my_dict = {"key1": "some_value", "key2": None}
catalog.save("my_dataset", my_dict)
```

### Additional parameters for `session.run()`
You can also specify the following optional arguments for `session.run()`:

```eval_rst
+---------------+----------------+-------------------------------------------------------------------------------+
| Argument name | Accepted types | Description                                                                   |
+===============+================+===============================================================================+
| tags          | Iterable[str]  | Construct the pipeline using only nodes which have this tag attached.         |
|               |                | A node is included in the resulting pipeline if it contains any of those tags |
+---------------+----------------+-------------------------------------------------------------------------------+
| runner        | AbstractRunner | An instance of Kedro [AbstractRunner](/kedro.runner.AbstractRunner);          |
|               |                | can be an instance of a [ParallelRunner](/kedro.runner.ParallelRunner)        |
+---------------+----------------+-------------------------------------------------------------------------------+
| node_names    | Iterable[str]  | Run only nodes with specified names                                           |
+---------------+----------------+-------------------------------------------------------------------------------+
| from_nodes    | Iterable[str]  | A list of node names which should be used as a starting point                 |
+---------------+----------------+-------------------------------------------------------------------------------+
| to_nodes      | Iterable[str]  | A list of node names which should be used as an end point                     |
+---------------+----------------+-------------------------------------------------------------------------------+
| from_inputs   | Iterable[str]  | A list of dataset names which should be used as a starting point              |
+---------------+----------------+-------------------------------------------------------------------------------+
| to_outputs    | Iterable[str]  | A list of dataset names which should be used as an end point                  |
+---------------+----------------+-------------------------------------------------------------------------------+
| to_outputs    | Iterable[str]  | A list of dataset names which should be used as an end point                  |
+---------------+----------------+-------------------------------------------------------------------------------+
| load_versions | Dict[str, str] | A mapping of a dataset name to a specific dataset version (timestamp)         |
|               |                | for loading - this applies to the versioned datasets only                     |
+---------------+----------------+-------------------------------------------------------------------------------+
| pipeline_name | str            | Name of the modular pipeline to run - must be one of those returned           |
|               |                | by register_pipelines function from src/<package_name>/pipeline_registry.py   |
+---------------+----------------+-------------------------------------------------------------------------------+
```

This list of options is fully compatible with the list of CLI options for the `kedro run` command. In fact, `kedro run` is calling `session.run()` behind the scenes.


## Global variables

Add customised global variables to `.ipython/profile_default/startup/00-kedro-init.py`. For example, if you want to add a global variable for `parameters` from `parameters.yml`, update `reload_kedro()` as follows:

```python
@register_line_magic
def reload_kedro(project_path, line=None):
    """Line magic which reloads all Kedro default variables."""
    # ...
    global parameters
    try:
        # ...
        session = KedroSession.create("<your-kedro-project-package-name>", project_path)
        _activate_session(session)
        context = session.load_context()
        parameters = context.params
        # ...
        logging.info(
            "Defined global variable `context`, `session`, `catalog` and `parameters`"
        )
    except:
        pass
```


## Convert functions from Jupyter notebooks into Kedro nodes

Built into the Kedro Jupyter workflow is the ability to convert multiple functions defined in the Jupyter notebook(s) into Kedro nodes. You need a single CLI command.

Here is how it works:

* Start a Jupyter notebook session: `kedro jupyter notebook`
* Create a new notebook and paste the following code into the first cell:

```python
def some_action():
    print("This function came from `notebooks/my_notebook.ipynb`")
```

* Enable tags toolbar: `View` menu -> `Cell Toolbar` -> `Tags`
![Enable the tags toolbar graphic](../meta/images/jupyter_notebook_workflow_activating_tags.png)

* Add the `node` tag to the cell containing your function
![Add the node tag graphic](../meta/images/jupyter_notebook_workflow_tagging_nodes.png)

```eval_rst
.. tip:: The notebook can contain multiple functions tagged as ``node``, each of them will be exported into the resulting Python file
```

* Save your Jupyter notebook to `notebooks/my_notebook.ipynb`
* Run `kedro jupyter convert notebooks/my_notebook.ipynb` from the terminal to create a Python file `src/<package_name>/nodes/my_notebook.py` containing `some_action` function definition


```eval_rst
.. tip:: You can also convert all your notebooks at once by calling ``kedro jupyter convert --all``.
```

* The `some_action` function can now be used in your Kedro pipelines

## Kedro-Viz and Jupyter

If you have [Kedro-Viz](https://github.com/kedro-org/kedro-viz) installed then you can display an interactive visualisation of your pipeline directly in your notebook using the [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html) `%run_viz`. You should see a visualisation like the following:

![](../meta/images/jupyter_notebook_kedro_viz.png)
