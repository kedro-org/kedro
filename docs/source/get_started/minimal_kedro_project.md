# Create a Minimal Kedro Project
This documentation aims to explain the essential components of a minimal Kedro project. The guide begins with a blank project and gradually introduces the necessary elements. While most users typically start with a [project template]((./new_project.md)) or adapt an existing Python project, this guide will help you understand the core concepts and how to customise them to suit your specific needs.

## Essential Components of a Kedro Project

Kedro is a Python framework designed for creating reproducible data science code. A typical Kedro project consists of two parts, the **mandatory structure** and the **opinionated** project structure**.

### 1. **Recommended Structure**
Kedro projects follow a specific directory structure that promotes best practices for collaboration and maintenance. The default structure includes:

| Directory/File        | Description                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| `conf/`               | Contains configuration files such as `catalog.yml` and `parameters.yml`.  |
| `data/`               | Local project data, typically not committed to version control.            |
| `docs/`               | Project documentation files.                                               |
| `notebooks/`          | Jupyter notebooks for experimentation and prototyping.                     |
| `src/`                | Source code for the project, including pipelines and nodes.                |
| `README.md`           | Project overview and instructions.                                         |
| `pyproject.toml`      | Metadata about the project, including dependencies.                        |
| `.gitignore`          | Specifies files and directories to be ignored by Git.                     |

### 2. **Mandatory Files**
For a project to be recognised as a Kedro project and support running `kedro run`, it must contain three essential files:
- **`pyprojec.toml`**: Defines the python project
- **`settings.py`**: Defines project settings, including library component registration.
- **`pipeline_registry.py`**: Registers the project's pipelines.

If you want to see some examples of these files, you can either create a project with `kedro new` or check out the [project template on GitHub](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas)


#### `pyproject.toml`
The `pyproject.toml` file is a crucial component of a Kedro project, serving as the standard way to store build metadata and tool settings for Python projects. It is essential for defining the project's configuration and ensuring proper integration with various tools and libraries.

Particularly, Kedro requires `[tool.kedro]` section in `pyproject.toml`, this describes the [project metadata](../kedro_project_setup/settings.md) in the project.

Typically, it looks similar to this:
```toml
[tool.kedro]
package_name = "package_name"
project_name = "project_name"
kedro_init_version = "kedro_version"
tools = ""
example_pipeline = "False"
source_dir = "src"
```

This informs Kedro where to look for the source code, `settings.py` and `pipeline_registry.py` are.

#### `settings.py`
The `settings.py` file is an important configuration file in a Kedro project that allows you to define various settings and hooks for your project. Here’s a breakdown of its purpose and functionality:
- Project Settings: This file is where you can configure project-wide settings, such as defining the logging level, setting environment variables, or specifying paths for data and outputs.
- Hooks Registration: You can register custom hooks in settings.py, which are functions that can be executed at specific points in the Kedro pipeline lifecycle (e.g., before or after a node runs). This is useful for adding additional functionality, such as logging or monitoring.
- Integration with Plugins: If you are using Kedro plugins, settings.py can also be utilized to configure them appropriately.

Even if you do not have any settings, an empty `settings.py` is still required. Typically, they are stored at `src/<package_name>/settings.py`.

#### `pipeline_registry.py`
The `pipeline_registry.py` file is essential for managing the pipelines within your Kedro project. It provides a centralized way to register and access all pipelines defined in the project. Here are its key features:
- Pipeline Registration: The file must contain a top-level function called `register_pipelines()` that returns a mapping from pipeline names to Pipeline objects. This function is crucial because it enables the Kedro CLI and other tools to discover and run the defined pipelines.
- Autodiscovery of Pipelines: Since Kedro 0.18.3, you can use the [`find_pipeline`](../nodes_and_pipelines/pipeline_registry.md#pipeline-autodiscovery) function to automatically discover pipelines defined in your project without manually updating the registry each time you create a new pipeline.

## Creating a Minimal Kedro Project Step-by-Step
This guide will walk you through the process of creating a minimal Kedro project, allowing you to successfully run `kedro run` with just three files.

### Step 1: Install Kedro

First, ensure that Python is installed on your machine. Then, install Kedro using pip:

```bash
pip install kedro
```

### Step 2: Create a New Kedro Project
Create a new directory for your project:
```bash
mkdir minikedro
```

Navigate into your newly created project directory:

```bash
cd minikiedro
```

### Step 3: Create `pyproject.toml`
Create a new file named `pyproject.toml` in the project directory with the following content:

```toml
[tool.kedro]
package_name = "minikedro"
project_name = "minikedro"
kedro_init_version = "0.19.9"
source_dir = "."
```

At this point, your workingn directory should look like this:
```bash
.
├── pyproject.toml
```


```{note}
Note we define `source_dir = "."`, usually we keep our source code inside a directory called `src`. For this example, we try to keep the structure minimal so we keep the source code in the root directory
```

### Step 4: Create `settings.py` and `pipeline_registry.py`
Next, create a folder named minikedro, which should match the package_name defined in pyproject.toml:

```bash
mkdir minikedro
```
Inside this folder, create two empty files: `settings.py` and `pipeline_registry.py`:

```bash
touch minikedro/settings.py minikedro/pipeline_registry.py
```

Now your working directory should look like this:
```bash
.
├── minikedro
│   ├── pipeline_registry.py
│   └── settings.py
└── pyproject.toml
```

Try running the following command in the terminal:
```bash
kedro run
```

You will encounter an error indicating that pipeline_registry.py is empty:
```bash
AttributeError: module 'minikedro.pipeline_registry' has no attribute 'register_pipelines'
```

### Step 5: Create a Simple Pipeline
To resolve this issue, add the following code to `pipeline_registry.py`, which defines a simple pipeline to run:

```python
from kedro.pipeline import pipeline, node

def foo():
    return "dummy"

def register_pipelines():
    return {"__default__": pipeline([node(foo, None, "dummy_output")])}
```

If you attempt to run the pipeline again with `kedro run`, you will see another error:
```bash
MissingConfigException: Given configuration path either does not exist or is not a valid directory: /workspace/kedro/minikedro/conf/base
```

### Step 6: Define the Project Settings
This error occurs because Kedro expects a configuration folder named `conf`, along with two environments called `base` and `local`.

To fix this, add these two lines into `settings.py`:
```python
CONF_SOURCE = "."
CONFIG_LOADER_ARGS = {"base_env": ".", "default_run_env": "."}
```

These lines override the default settings so that Kedro knows to look for configurations in the current directory instead of the expected conf folder. For more details, refer to [How to change the setting for a configuration source folder](../configuration/configuration_basics.md#how-to-change-the-setting-for-a-configuration-source-folder) and [Advance Configuration without a full Kedro project](../configuration/advanced_configuration.md#advanced-configuration-without-a-full-kedro-project)

Now, run the pipeline again:
```bash
kedro run
```

You should see that the pipeline runs successfully!

## Conclusion

Kedro provides a structured approach to developing data pipelines with clear separation of concerns through its components and directory structure. By following the steps outlined above, you can set up a minimal Kedro project that serves as a foundation for more complex data processing workflows. This guide explains essential concepts of Kedro projects. If you already have a Python project and want to integrate Kedro into it, these concepts will help you adjust and fit your own needs.
