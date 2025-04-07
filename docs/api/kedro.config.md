# kedro.config

::: kedro.config
    options:
      docstring_style: google
      members: false
      show_source: false

| Name                     | Type       | Description                     |
|--------------------------|------------|---------------------------------|
| [`kedro.config.AbstractConfigLoader`](#kedro.config.AbstractConfigLoader) | Class      | Abstract base class for config loaders. |
| [`kedro.config.OmegaConfigLoader`](#kedro.config.OmegaConfigLoader)       | Class      | Config loader that uses OmegaConf. |
| [`kedro.config.MissingConfigException`](#kedro.config.MissingConfigException) | Exception  | Raised when a required config is missing. |

::: kedro.config.AbstractConfigLoader
    options:
      members: true
      show_source: true

::: kedro.config.OmegaConfigLoader
    options:
      members: true
      show_source: true

::: kedro.config.MissingConfigException
    options:
      members: true
      show_source: true