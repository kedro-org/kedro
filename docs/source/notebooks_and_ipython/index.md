# Kedro for notebook users


If you are familiar with notebooks, you probably find their liberal development environment perfect for exploratory data analysis and experimentation.

As project complexity increases, particularly if you work collaboratively, you may decide to transition to Kedro's way of working to organise your code into a shareable project. There is no single way to switch between notebooks and Kedro. It's possible to pair both ways of working and gradually introduce Kedro techniques into your notebook code.

**Add Kedro to your existing notebook project**

The page titled [Convert a notebook to Kedro](??) describes how to convert your notebook project to use Kedro in increments. It starts with the basics of configuration loading, then adds Kedro's data management approach, and finally introduces nodes and pipelines.

**Add a notebook to your existing Kedro project**
The page titled [Use a Jupyter notebook for Kedro project experiments](./kedro_and_notebooks.md) describes how to set up a notebook to access the elements of a Kedro project for experimentation. If you have an existing Kedro project but want to use notebook features to explore your data and experiment with pipelines, this is the page to start.

**Use Kedro's Data Catalog within a notebook**
If you want to start a new notebook project but take advantage of the Data Catalog, a key Kedro feature, [Kedro as a data registry](./kedro_as_a_data_registry.md) explains how to proceed.



```{toctree}
:maxdepth: 1

add_kedro_to_a_notebook.ipynb
kedro_and_notebooks
kedro_as_a_data_registry
```
