# Kedro for notebook users


If you are familiar with notebooks, you probably find their liberal development environment perfect for exploratory data analysis and experimentation.

Kedro makes it easier to organise your code into a shareable project, and you may decide to transition to Kedro for collaboration purposes, or if your code becomes more complex.

There is flexibility in the ways you can combine notebooks and Kedro. For example, it's possible to gradually introduce Kedro techniques into your notebook code. Likewise, it is possible to take a Kedro project and add a notebooks to explore data or experimental features.

**Add Kedro to your existing notebook project**
The page titled [Add Kedro features to a notebook](./notebook-example/add_kedro_to_a_notebook.md) describes how to convert your notebook project to use Kedro in increments. It starts with the basics of configuration loading, then adds Kedro's data management approach, and finally introduces nodes and pipelines.

**Add a notebook to your existing Kedro project**
The page titled [Use a Jupyter notebook for Kedro project experiments](./kedro_and_notebooks.md) describes how to set up a notebook to access the elements of a Kedro project for experimentation. If you have an existing Kedro project but want to use notebook features to explore your data and experiment with pipelines, this is the page to start.

```{toctree}
:maxdepth: 1
:hidden:

notebook-example/add_kedro_to_a_notebook
kedro_and_notebooks
```
