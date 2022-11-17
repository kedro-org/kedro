# Kedro and Jupyter Notebooks


There are reasons why you may want to use a Jupyter Notebook:

* To get up and running fast as you conduct exploratory data analysis
* For experimentation as you create new Python functions 
* As a tool for reporting and presentations

Longer term, a project based around Notebooks may run into problems when you try to scale it because of [lack of support for versioning, reproducibility, and modularity](https://towardsdatascience.com/5-reasons-why-you-should-switch-from-jupyter-notebook-to-scripts-cb3535ba9c95). 

As soon as you reach a point where you need to use software best practice to control your complexity, it becomes clear that Notebooks don’t support those ideals.

Another issue that hits data scientists in teams is that of environment reproducibility. Suppose you want to collaborate with a colleague and share your Notebook. But what if they are using a different version of a particular package, such as sklearn, that has changed over time? How do you specify to your colleague what environment to set up so they can run the Notebook just as you do on your machine? How do you automate that setup? Going further: you want to deploy the code to a number of people in the team as part of a demo. But how do you manage configuration and updates? Don’t even think about how to make a release and product-ise your Notebook!

you can also transform an existing Notebook to a Kedro project, as a recent video from DataEngineerOne illustrates

Once you have set up a Kedro project, you can use a Jupyter Notebook to develop your code if you prefer that way of working, and then transform it into a Kedro node, which is a Python function that is called by the Kedro framework in its role of managing the pipeline. 

There are some neat extensions that allow you to work in a Notebook while developing your Kedro project, and you can find a video of how to use two tricks to make Jupyter Notebooks more useful with Kedro.

It is opinionated to keep you aligned with software best practices, but it also allows you the option of using a Jupyter Notebook for experimentation, and eases the transfer of code from the Notebook into the Kedro project.

## Use Kedro as a data registry for a Notebook project

One way to make it easier to share a Jupyter notebook with others, is to avoid the use of hard-coded file paths to load or save data. You may want to use Kedro's [`DataCatalog`](../data/data_catalog.md) as a registry for your data, without using any of the other features of Kedro.

The Kedro starter with alias `standalone-datacatalog` (formerly known as `mini-kedro`) provides minimal functionality so you can use YAML to specify the sources required to load and save data:

 ```yaml
# conf/base/catalog.yml
example_dataset_1:
  type: pandas.CSVDataSet
  filepath: folder/filepath.csv

example_dataset_2:
  type: spark.SparkDataSet
  filepath: s3a://your_bucket/data/01_raw/example_dataset_2*
  credentials: dev_s3
  file_format: csv
  save_args:
    if_exists: replace
```


This makes it possible to interact with data within your Jupyter notebook, with code much like this:

```python
df = catalog.load("example_dataset_1")
df_2 = catalog.save("example_dataset_2")
```

### Usage

Use the [`standalone-datacatalog` starter](https://github.com/kedro-org/kedro-starters/tree/main/standalone-datacatalog) to create a new project:

```bash
kedro new --starter=standalone-datacatalog
```


The starter comprises a minimal setup to use the traditional [Iris dataset](https://www.kaggle.com/uciml/iris) with Kedro's [`DataCatalog`](../data/data_catalog.md).

The starter contains:

* A `conf` directory, which contains an example `DataCatalog` configuration (`catalog.yml`)
* A `data` directory, which contains an example dataset identical to the one used by the [`pandas-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris) starter
* An example notebook, which shows how to instantiate the `DataCatalog` and interact with the example dataset
* A blank `README.md` file, which points to this page of documentation


Should you later want to transition to use Kedro for the project, you can simply create a new empty Kedro project and copy the `conf` and `data` directories from your `standalone-datacatalog` starter project over to your new project