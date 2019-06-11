# Working with Kedro and IPython

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

In order to experiment with the code interactively, you may want to use a Python kernel inside a Jupyter notebook (formerly known as IPython).

To start a standalone IPython session, run the following command in the root directory of the project:

```bash
kedro ipython
```

Every time you start/restart an IPython session, a startup script (`<your_project_name>/.ipython/profile_default/startup/00-kedro-init.py`) will add the following variables in scope:

- `proj_dir` (`str`) - Root directory of the project
- `proj_name` (`str`) - Project folder name
- `conf` (`ConfigLoader`) - Configuration loader object
- `io` (`DataCatalog`) - Data catalog
- `parameters` (`dict`) - Parameters from the project configuration
- `startup_error` (`Exception`) - An error that was raised during the execution of the startup script or `None` if no errors occurred.

To reload these at any point (e.g., if you updated `catalog.yml`) use the [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html) `%reload_kedro`. This magic can also be used to see the error message if any of the variables above are undefined.

## Loading `DataCatalog` in IPython

You can load a dataset of [Iris Test example](https://archive.ics.uci.edu/ml/datasets/iris) inside the IPython console, by simply executing the following:

```python
io.load("example_iris_data").head()
```

> Since the `io` is already defined during IPython session startup, we don't have to recreate it.

```bash
kedro.io.data_catalog - INFO - Loading data from `example_iris_data` (CSVLocalDataSet)...

   sepal_length  sepal_width  petal_length  petal_width species
0           5.1          3.5           1.4          0.2  setosa
1           4.9          3.0           1.4          0.2  setosa
2           4.7          3.2           1.3          0.2  setosa
3           4.6          3.1           1.5          0.2  setosa
4           5.0          3.6           1.4          0.2  setosa
```

When you have finished, you can exit IPython by typing:

```python
exit()
```
