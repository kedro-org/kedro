# Set up the spaceflights project

This section shows how to create a new project with `kedro new` using the [Kedro spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas)) and install project dependencies (with `pip install -r requirements.txt`).

## Create a new project

Navigate to the folder you want to store the project. Type the following to generate the project from the [Kedro spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas). The project will be populated with a complete set of working example code:

```bash
uvx kedro new --starter spaceflights-pandas --name spaceflights
```

!!! note
    Using `uvx` lets you run Kedro without installing it into your system or virtual environment. It downloads and runs Kedro in a clean temporary environment each time. If you prefer a standard installation (e.g. pip + virtual environment), see the [installation guide](../getting-started/install.md#alternative-methods).

After Kedro has created the project, navigate to the [project root directory](./spaceflights_tutorial.md#project-root-directory):

```bash
cd spaceflights
```

Next, to create a virtual environment and install the dependencies, run

```bash
uv sync
```

Finally, verify that your installation is correct:

```bash
uv run kedro info
```

See the documentation for more information and alternative methods to [set up Kedro](../getting-started/install.md).

!!! tip
    We recommend that you use the same version of Kedro that was most recently used to test this tutorial (0.19.0). To check the version installed, type `kedro -V` in your terminal window.

## Optional: logging and configuration

You might want to [set up logging](../develop/logging.md) at this stage of the workflow, but we do not use it in this tutorial.

You may also want to store credentials such as usernames and passwords if they are needed for specific data sources used by the project.

To do this, add them to `conf/local/credentials.yml` (some examples are included in that file for illustration).

### Configuration best practice to avoid leaking confidential data

* Do not commit data to version control.
* Do not commit notebook output cells (data can easily sneak into notebooks when you don't delete output cells).
* Do not commit credentials in `conf/`. Use only the `conf/local/` folder for sensitive information like access credentials.

You can find additional information in the [documentation on configuration](../configure/configuration_basics.md).
