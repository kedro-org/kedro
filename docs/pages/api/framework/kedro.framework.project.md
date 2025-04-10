::: kedro.framework.project
    options:
      docstring_style: google
      members: false
      show_source: false

| Function                          | Description                                                                 |
|-----------------------------------|-----------------------------------------------------------------------------|
| [`configure_logging`](#kedro.framework.project.configure_logging) | Configure logging according to the `logging_config` dictionary.            |
| [`configure_project`](#kedro.framework.project.configure_project) | Configure a Kedro project by populating its settings with values defined in `settings.py` and `pipeline_registry.py`. |
| [`find_pipelines`](#kedro.framework.project.find_pipelines)       | Automatically find modular pipelines having a `create_pipeline` function.   |
| [`validate_settings`](#kedro.framework.project.validate_settings) | Eagerly validate that the settings module is importable if it exists.       |


::: kedro.framework.project.configure_logging
    options:
      show_source: true

::: kedro.framework.project.configure_project
    options:
      show_source: true

::: kedro.framework.project.find_pipelines
    options:
      show_source: true

::: kedro.framework.project.validate_settings
    options:
      show_source: true