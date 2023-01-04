# Configuration with OmegaConf

[OmegaConf](https://omegaconf.readthedocs.io/) is a python library for dealing with configuration. It is a YAML based hierarchical configuration system, with support for merging configurations from multiple sources.
From Kedro 0.18.5 you can use the [`OmegaConfLoader`](/kedro.config.OmegaConfLoader) which uses `OmegaConf` under the hood to load data.

The `OmegaConfLoader` is different from the `ConfigLoader` and `TemplatedConfigLoader` in a couple of ways:
* `OmegaConfLoader` can only load `YAML` and `JSON` files. Acceptable file extensions are `.yml`, `.yaml`, and `.json`.
* `OmegaConfLoader` handles templating differently. An example can be found below. 

To use the `OmegaConfLoader` in your project, set the `CONFIG_LOADER_CLASS` constant in your [`src/<package_name>/settings.py`](settings.md):

```python
from kedro.config import OmegaConfLoader  # new import

CONFIG_LOADER_CLASS = OmegaConfLoader
```


# Setting config directly on loader instance
  
