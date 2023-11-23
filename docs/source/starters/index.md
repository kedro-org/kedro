# New project tools
As you saw from the [First steps](../get_started/new_project.md) section, once you have [set up Kedro](../get_started/install.md), you can use `kedro new` to create a basic Kedro project containing project directories and basic code, which you can configure depending on the tooling and example code you need.

There are several ways to create a new Kedro project, which the pages in this section describe in detail.

```{toctree}
:maxdepth: 1
:hidden:

new_project_tools
starters
```

**Use `kedro new` to create a basic project** <br />
In the simplest instance, you can create a project using `kedro new` and select from a range of [tools and example code options](./new_project_tools.md) to extend the basic project.

**Use `kedro new` with `--config`** <br />
Similarly, you can use `kedro new` but additionally pass in a configuration file, for example:

```bash
kedro new --config=config.yml
```

The file enables you to customise details such as the project folder name and package name.

The configuration file must contain:

* `output_dir` The path in which to create the project directory, which can be set to `~` for the home directory or `.` for the current working directory
* `project_name`
* `repo_name`
* `python_package`
* TO DO -- tools and example code options

The `output_dir` can be specified as `~` for the home directory or `.` for the current working directory. Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: My First Kedro Project
repo_name: testing-kedro
python_package: test_kedro
```

**Use `kedro new` with a `--starter`** <br />
Alternatively, you can create a new Kedro project with a [starter](./starters.md) that adds a set of code for a common project use case.
