# Kedro for notebook users


As a data practitioners you are likely to be familiar with notebooks and find their liberal development environment perfect for exploratory data analysis and experimentation.

As project complexity increases, particularly if you work collaboratively, you may decide to transition to Kedro's way of working to organise your code into a shareable project. There is no single switch to flick between notebooks and Kedro; it's possible to pair both ways of working and gradually introduce Kedro techniques into your notebook code.

**Add Kedro to your existing notebook project**

This documentation section describes how to introduce Kedro to your notebook project. The page titled []() starts with the basics of configuration loading, then adds Kedro's data management approach, and finally introduces nodes and pipelines.

**Add a notebook to your existing Kedro project**
The page titled [Use a Jupyter notebook for Kedro project experiments](./kedro_and_notebooks.md) describes how to set up a notebook to access the elements of a Kedro project for experimentation. If you have an existing Kedro project but want to use notebook features to explore your data and experiment with pipelines, this is the page to start.

**Use Kedro's Data Catalog within a notebook**
If you want to start a new notebook project but take advantage of the Data Catalog, a key Kedro feature, [Kedro as a data registry](./kedro_as_a_data_registry.md) explains how to proceed.



```{toctree}
:maxdepth: 1


kedro_and_notebooks
kedro_as_a_data_registry
```
