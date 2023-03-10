# Create a new Kedro project

There are a few ways to create a new project once you have [installed Kedro](install.md). For example, you can create a basic Kedro project set up with the project directories and basic code, but empty to extend as you need. Alternatively, you can create a Kedro project populated with template code that acts as a starter example.

## Create a new empty project

The simplest way to create a default Kedro project is to navigate to your preferred directory and type:

```bash
kedro new
```

You will be asked to enter a name for your project, which can be human-readable and may contain alphanumeric symbols, spaces, underscores and hyphens. It must be at least two characters long.

Your choice is set as the value of `project_name` and is used to generate the `repo_name` and `python_package` automatically.

So, if you enter "Get Started", the directory name for the project (`repo_name`) is automatically set to be `get-started`, and the Python package name (`python_package`) for your project is set to be `get_started`.

| Description                                                     | Setting          | Example       |
| --------------------------------------------------------------- | ---------------- | ------------- |
| A human-readable name for your new project                      | `project_name`   | `Get Started` |
| Local directory to store your project                           | `repo_name`      | `get-started` |
| The Python package name for your project (short, all-lowercase) | `python_package` | `get_started` |


The output of `kedro new` is a directory containing all the project files and subdirectories required for a basic Kedro project, ready to extend with your own code.

### Create a new project from a configuration file

If you prefer to customise your new project's directory and package name, you can instead use a configuration file to specify those values. The configuration file must contain:

-   `output_dir` The path in which to create the project directory
-   `project_name`
-   `repo_name`
-   `python_package`

The `output_dir` can be set to wherever you want to create the project. For example, `~` for your home directory, or `.` for the current working directory. Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: My First Kedro Project
repo_name: testing-kedro
python_package: test_kedro
```

To create this new project:

```bash
kedro new --config=<path>/config.yml
```

## Create a new project containing example code

You can use a [Kedro Starter](../kedro_project_setup/starters.md) to create a project containing template code, to run as-is or to adapt and extend.

To illustrate, we will create a Kedro project with example code based on the familiar [Iris dataset](https://www.kaggle.com/uciml/iris).

### Background information for the iris dataset example
The dataset was generated in 1936 by the British statistician and biologist Ronald Fisher. The dataset contains 150 samples in total, comprising 50 samples of 3 different species of Iris plant (Iris Setosa, Iris Versicolour and Iris Virginica). For each sample, the flower measurements are recorded for the sepal length, sepal width, petal length and petal width.

![](../meta/images/iris_measurements.png)

A machine learning model can use the Iris dataset to illustrate classification (a method used to determine the type of an object by comparison with similar objects that have previously been categorised). Once trained on known data, the machine learning model can make a predictive classification by comparing a test object to the output of its training data.

### Create the example project

The first step is to create the Kedro project using a starter to add the example code and data. Feel free to name your project as you like, but here we will assume the project's name is `get started`.

```bash
kedro new --starter=pandas-iris
```

### Run the example project

Once you have created the project, to run project-specific Kedro commands, you must navigate to the directory in which it has been created and install the project's dependencies:

```bash
cd get-started
pip install -r src/requirements.txt
```

You are ready to run the project:

```bash
kedro run
```

```{note}
The first time you type a `kedro` command in your new project, you will be asked whether you wish to opt into [usage analytics](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry). Your decision is recorded in the `.telemetry` file so that subsequent calls to `kedro` in this project do not ask you again.
```

When the command completes, you should see a log message similar to the following in your console:

```
[08/09/22 11:23:30] INFO     Model has accuracy of 0.933 on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```

### Under the hood: Pipelines and nodes

The example project contains a single pipeline stored in `src/get_started/pipeline.py`. The pipeline is comprised of nodes that are responsible for splitting the data into training and testing samples, running the 1-nearest neighbour algorithm to make predictions and accuracy-reporting.

The nodes are stored in `src/get_started/nodes.py`:

| Node            | Description                                                                         | Node function name |
| --------------- | ----------------------------------------------------------------------------------- | ------------------ |
| Split data      | Splits the example Iris dataset into train and test samples                         | `split_data`       |
| Make Predictions| Makes class predictions (using 1-nearest neighbour classifier and train-test set)   | `make_predictions` |
| Report accuracy | Reports the accuracy of the predictions performed by the previous node.             | `report_accuracy`  |

### Visualise the project

This is a swift introduction to show how to visualise the project with Kedro-Viz. See the [visualisation documentation](../visualisation/kedro-viz_visualisation) for more detail.

The Kedro-Viz package needs to be installed separately as it is not part of the standard Kedro installation:

```bash
pip install kedro-viz
```

In your terminal type the following:

```bash
kedro viz
```

This command automatically opens a browser tab to serve the visualisation at `http://127.0.0.1:4141/`.

You should see the following, which you can explore to learn more about the pipeline, nodes and datasets:

![](../meta/images/pipeline_visualisation.png)

To exit the visualisation, close the browser tab. To regain control of the terminal, enter `^+c` on Mac or `Ctrl+c` on Windows or Linux machines.
