# Set up PyCharm

This section will present a quick guide on how to configure [PyCharm](https://www.jetbrains.com/pycharm/) as a development environment for working on Kedro projects.

Open a new project directory in PyCharm. You will need to add your **Project Interpreter**, so go to **PyCharm | Preferences** for macOS or **File | Settings** for Windows and Linux:

![](../meta/images/pycharm_preferences.png)

Choose **Project Interpreter**: <br />

![](../meta/images/pycharm_project_interpreter.png)

Click the cog on the right-hand side and click **Add**:

![](../meta/images/pycharm_add_interpreter.png)

Select **Conda Environment**:

![](../meta/images/pycharm_add_conda_env.png)

Choose **Existing environment** and navigate your way to find your existing environment. If you don't see your `conda` environment in the dropdown menu then you need to open a `terminal` / `command prompt` with your `conda` environment activated and run:

```console
# macOS / Linux
which python
# Windows
python -c "import sys; print(sys.executable)"
```

Paste the interpreter path into the file picker and click **OK**: <br />

![](../meta/images/pycharm_select_conda_interpreter.png)

Finally, in the **Project Explorer** right-click on `src` and then go to **Mark Directory as | Sources Root**:

![](../meta/images/pycharm_mark_dir_as_sources_root.png)


## Set up Run configurations

[PyCharm Run configurations](https://www.jetbrains.com/help/pycharm/creating-run-debug-configuration-for-tests.html) allow you to execute preconfigured scripts rapidly in your IDE with a click of a button. This may be useful for testing, running and packaging your Kedro projects.

Here we will walk you through an example of how to set up Run configuration for the Kedro CLI `run` command. It is also applicable to other Kedro commands, such as `test` or `install`.

Go to **Run | Edit Configurations**:

![](../meta/images/pycharm_edit_confs.png)

Add a new **Python** Run configuration:

![](../meta/images/pycharm_add_py_run_config.png)

Specify the **Run / Debug Configuration** name in the **Name** field, and edit the new Run configuration as follows:

- Pick **Module** from the dropdown
- Enter ``kedro`` in the **Module Name** field
- Enter ``run`` in the **Parameters** field
- Enter the path of your project directory into the **Working directory** field
- Pick ``Emulate terminal in output console`` from the **Modify options** dropdown, and then click **OK**

![](../meta/images/pycharm_edit_py_run_config.png)

```{note}
**Emulate terminal in output console** enables PyCharm to show [rich terminal output](../logging/index.md).
```

To execute the Run configuration, select it from the **Run / Debug Configurations** dropdown in the toolbar (if that toolbar is not visible, you can enable it by going to **View > Toolbar**). Click the green triangle:

![](../meta/images/pycharm_conf_run_button.png)

You may also select **Run** from the toolbar and execute from there. <br />

![](../meta/images/pycharm_conf_run_dropdown.png)

For other `kedro` commands, follow same steps but replace `run` in the `Parameters` field with the other commands that are to be used (e.g., `jupyter`, `package`, `registry` etc.).


## Debugging

To debug, simply click the line number in the source where you want execution to break:

![](../meta/images/pycharm_add_breakpoint.png)

Then click the bug button in the toolbar (![](../meta/images/pycharm_debugger_button.png)) and execution should stop at the breakpoint:

![](../meta/images/pycharm_debugger_break.png)

>For more information about debugging with PyCharm take a look at the [debugging guide on jetbrains.com](https://www.jetbrains.com/help/pycharm/part-1-debugging-python-code.html).


## Advanced: Remote SSH interpreter

```{note}
This section uses features supported in PyCharm Professional Edition only.
```

Firstly, add an SSH interpreter. Go to **Preferences | Project Interpreter** as above and proceed to add a new interpreter. Select **SSH Interpreter** and fill in details of the remote computer:

![](../meta/images/pycharm_ssh_interpreter_1.png)

Click **Next** and add the SSH password or SSH private key:

![](../meta/images/pycharm_ssh_interpreter_2.png)

Click **Next** and add the path of the remote interpreter. Assuming a Unix-like OS, this can be found by running `which python` within the appropriate `conda` environment on the remote computer.

![](../meta/images/pycharm_ssh_interpreter_3.png)

Click **Finish**. Go to **Run / Debug Configurations** to add a **Remote Run**. Select the remote interpreter that you have just created. For the script path, get the path of the Kedro CLI on the remote computer by running `which kedro` (macOS / Linux) in the appropriate environment.

![](../meta/images/pycharm_ssh_runner.png)

Click **OK** and then select **Remote Run** from the toolbar and click **Run** to execute remotely.

![](../meta/images/pycharm_remote_run.png)

[To debug remotely, click the debugger button as described above](#debugging).


## Advanced: Docker interpreter

```{note}
This section uses features supported by PyCharm Professional Edition only.
```

First, add a Docker interpreter. Go to **Preferences | Project Interpreter** as above and proceed to add a new interpreter. Select **Docker Interpreter** and then choose the target Docker image:

![](../meta/images/pycharm_docker_interpreter_1.png)

Click **OK** and check that the required packages appear:

![](../meta/images/pycharm_docker_interpreter_2.png)

Click **OK** and wait for PyCharm to index your new Python interpreter.

Click **OK**. Go to **Run / Debug Configurations** to add a **Python Run**. For the script path, get the path to the Kedro CLI on an instantiated image by running `which kedro` (macOS / Linux) in a container environment. Specify `run` as the parameter. Specify your working directory as the directory that contains your Kedro project on your local machine. Optional: Edit the Docker container volume mount setting if it does not match the directory that contains your Kedro project directory.

![](../meta/images/pycharm_docker_interpreter_3.png)

Click **OK** and then select your run configuration from the toolbar and click **Run** to execute.

[To debug, click the debugger button as described above](#debugging).

## Configure Python Console

You can configure Pycharm's IPython to load Kedro's Extension.

Click **PyCharm | Preferences** for macOS or **File | Settings**, inside **Build, Execution, Deployment** and **Console**, enter the **Python Console** configuration.

You can append the configuration necessary to use Kedro IPython to the **Starting script**:

```
%load_ext kedro.ipython
```

With this configuration, when you create a Python Console you should be able to use context, session and catalog.

![](../meta/images/pycharm_ipython_working_example.png)

## Configuring the Kedro catalog validation schema

You can enable the Kedro catalog validation schema in your PyCharm IDE to enable real-time validation, autocompletion and see information about the different fields in your `catalog` as you write it. To enable this, open a `catalog.yml` file and you should see "No JSON Schema" in the bottom right corner of your window. Click it and select "Edit Schema Mapping".

![](../meta/images/pycharm_edit_schema_mapping.png)

Add a new mapping using the "+" button in the top left of the window and select the name you want for it. Enter this URL `https://raw.githubusercontent.com/kedro-org/kedro/develop/static/jsonschema/kedro-catalog-0.18.json` in the "Schema URL" field and select "JSON Schema Version 7" in the "Schema version" field.

Add the following file path pattern to the mapping: `conf/**/*catalog*`.

![](../meta/images/pycharm_catalog_schema_mapping.png)

> [Different schemas for different Kedro versions can be found in the Kedro repository](https://github.com/kedro-org/kedro/tree/main/static/jsonschema).
