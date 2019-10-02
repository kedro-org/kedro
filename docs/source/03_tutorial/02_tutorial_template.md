# Kedro Spaceflights tutorial

In this tutorial, we will follow the [Kedro workflow](./01_workflow.md#development-workflow) and walk you through the steps necessary to convert an empty template into a working project. Our project will be based on the following scenario:

> _It is 2160 and the space tourism industry is booming. Globally, there are thousands of space shuttle companies taking tourists to the Moon and back. You have been able to source amenities offered in each space shuttle, customer reviews and company information. You want to construct a model for predicting the price for each trip to the Moon and the corresponding return flight._


## Creating the tutorial project

Run `kedro new` from your chosen working directory to create an empty template project, following the interactive prompts to set the project's name, repository / folder name and Python package name, [as previously described](../02_getting_started/03_new_project.md).

Call the project **`Kedro Tutorial`** and keep the default naming by pressing enter when prompted. Choose `N` to create a project template _without_ the Iris dataset example. Alternatively, you can create a new project from a [configuration file](../02_getting_started/03_new_project.md#create-a-new-project-from-a-configuration-file).

### Install project dependencies

Within your [virtual environment](../02_getting_started/03_new_project.md#install-project-dependencies) and your project's root directory, you can install project dependencies by running:

```bash
kedro install
```

### Project configuration

The project template has a default configuration, but you should reconfigure it as follows:

* Move `credentials.yml` from `conf/base/` to `conf/local/`
  - To do this in the terminal, type the following from within the project's root directory: `mv ./conf/base/credentials.yml ./conf/local/`.
* [optional] Add in any credentials to `conf/local/credentials.yml` that you would need to load specific data sources like usernames and passwords. Some examples are given within the file to illustrate how you store credentials.
* [optional] Set up local configuration. Additional information can be found in the section on [configuration](../04_user_guide/03_configuration.md) in the user guide.
* [optional] Set up [logging](../04_user_guide/07_logging.md).
