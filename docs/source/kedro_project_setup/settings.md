# Project settings

A Kedro project's `settings.py` file contains the application settings for the project, including registration of hooks and library components. This page explains how settings work and which settings are available.

```{note}
Application settings is distinct from `run time configuration <configuration.md>`_, which is stored in the ``conf`` folder and can vary by configuration environment, and `pyproject.toml <../faq/architecture_overview.md#kedro-project>`_ , which provides project metadata and build configuration.
```

By default, all code in `settings.py` is commented out. In the case that settings are not supplied, Kedro chooses sensible default values. You only need to edit `settings.py` if you wish to change to values other than the defaults.

```eval_rst
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| Setting                           | Default value                                           | Use                                                                                                                  |
+===================================+=========================================================+======================================================================================================================+
| :code:`HOOKS`                     | :code:`tuple()`                                         | Inject additional behaviour into the execution timeline with `project hooks <../extend_kedro/hooks.md>`_.            |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`DISABLE_HOOKS_FOR_PLUGINS` | :code:`tuple()`                                         | Disable `auto-registration of Hooks from plugins <../extend_kedro/hooks.md#disable-auto-registered-plugins-hooks>`_. |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`SESSION_STORE_CLASS`       | :code:`kedro.framework.session.session.BaseSessionStore`| Customise how `session data <session.md>`_ is stored.                                                                |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`SESSION_STORE_ARGS`        | :code:`dict()`                                          | Keyword arguments for the :code:`SESSION_STORE_CLASS` constructor.                                                   |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`CONTEXT_CLASS`             | :code:`kedro.framework.context.KedroContext`            | Customise how Kedro library components are managed.                                                                  |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`CONF_SOURCE`               | :code:`"conf"`                                          | Directory that holds `configuration <configuration.md>`_.                                                            |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`CONFIG_LOADER_CLASS`       | :code:`kedro.config.ConfigLoader`                       | Customise how project configuration is handled.                                                                      |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`CONFIG_LOADER_ARGS`        | :code:`dict()`                                          | Keyword arguments for the :code:`CONFIG_LOADER_CLASS` constructor.                                                   |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
| :code:`DATA_CATALOG_CLASS`        | :code:`kedro.io.DataCatalog`                            | Customise how the `Data Catalog <../data/data_catalog.md>`_ is handled.                                              |
+-----------------------------------+---------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------+
```
