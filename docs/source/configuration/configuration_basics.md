# Configuration

This section contains detailed information about Kedro project configuration. Project configuration is the configuration inside the [`/conf`](../get_started/kedro_concepts.md#conf) directory of your Kedro project.
By default, the files stored in this directory allow you to configure [parameters](configuration.md#parameters), [credentials](configuration.md#credentials), the [data catalog](../data/data_catalog.md), and [logging](../logging/logging.md).

Kedro makes use of a configuration loader to load any project configuration files. The available configuration loader classes are: [`ConfigLoader`](/kedro.config.ConfigLoader), [`TemplatedConfigLoader`](/kedro.config.TemplatedConfigLoader), and [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader).
By default, Kedro uses the `ConfigLoader`, for which the relevant API documentation can be found in [kedro.config.ConfigLoader](/kedro.config.ConfigLoader). In the following sections and examples, you can assume the default `ConfigLoader` is used, unless otherwise specified.


## Configuration basics

### Configuration source
The configuration source is the source folder where the Kedro project configuration is stored. We recommend that you keep all configuration files in the default `conf` directory of a Kedro project. 

### Configuration environments
...

#### Local 
The `local` folder should be used for configuration that is either user-specific (e.g. IDE configuration) or protected (e.g. security keys).

```{note}
Please do not check in any local configuration to version control.
```

#### Base 
The `base` folder is for shared configuration, such as non-sensitive and project-related configuration that may be shared across team members.

```{warning}
Do not put access credentials in the base configuration folder or any other configuration environment directory that is set up with version control.
```

### Configuration loading
Kedro-specific configuration (e.g., `DataCatalog` configuration for IO) is loaded using a configuration loader class, by default, the `ConfigLoader` class.
When you interact with Kedro through the command line, e.g. by running `kedro run`, Kedro will load all project configuration in the configuration source through this configuration loader.

The loader recursively scans for configuration files inside the `conf` directory, firstly in the `conf/base/` (`base` being the default environment) and then in the `conf/local/` (`local` being the designated overriding environment) directory.
Files will be matched according to file name and type rules. Suppose the config loader needs to fetch the catalog configuration, it will search according to the following rules:

* *Either* of the following is true:
  * filename starts with `catalog`
  * file is located in a sub-directory whose name is prefixed with `catalog`
* *And* file extension is one of the following: `yaml`, `yml`, `json`, `ini`, `pickle`, `xml` or `properties` for the `ConfigLoader` and `TemplatedConfigLoader` or `yaml`, `yml`, or `json` for the `OmegaConfigLoader`.


## Basic configuration how-tos 

### How to change the configuration source folder?
If you prefer to store the Kedro project configuration in a different directory than the `conf` directory inside your project you can change the configuration source by setting the `CONF_SOURCE` variable in [`src/<package_name>/settings.py`](settings.md) as follows:

```python
CONF_SOURCE = "new_conf"
```

### How to change the configuration source folder at run time?
You can specify a source directory for the configuration files at run time using the [`kedro run` CLI command](../development/commands_reference.md#modifying-a-kedro-run) with the `--conf-source` flag as follows:

```bash
kedro run --conf-source=<path-to-new-conf-directory>
```

### How to read configuration from a compressed file? (POTENTIALLY ADVANCED QUESTION)
You can read configuration from a compressed file in `tar.gz` or `zip` format by using the [`OmegaConfigLoader`](/kedro.config.OmegaConfigLoader).
The two commands below are examples of how to reference a `tar.gz` or `zip` file:

 ```bash
kedro run --conf-source=<path-to-compressed-file>.tar.gz

kedro run --conf-source=<path-to-compressed-file>.zip
```

To compress your configuration you can either leverage Kedro's `kedro package` command which builds the package into the `dist/` folder of your project, and creates one `.egg` file, one `.whl` file, as well as a `tar.gz` file containing the project configuration. This compressed version of the config files excludes any files inside your `local` directory.
Alternatively you can run the command below to create a `tar.gz` file:

```bash
tar --exclude=local/*.yml -czf <my_conf_name>.tar.gz --directory=<path-to-conf-dir> <conf-dir>
```

Or the following command to create a `zip` file:

```bash
zip -x <conf-dir>/local/** -r <my_conf_name>.zip <conf-dir>
```

Note that for both the `tar.gz` and `zip` file the following structure is expected:

```text
<conf_dir>
├── base               <-- the files inside be different, but this is an example of a standard Kedro structure.
│   └── parameters.yml
│   └── catalog.yml
└── local              <-- the top level local directory is required, but no files should be inside when distributed.
└── README.md          <-- optional but included with the default Kedro conf structure.
```

#### How to directly access configuration for e.g. debugging?
If you want to directly access configuration in code, for example to debug, you can do so as follows:

```python
from kedro.config import ConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = ConfigLoader(conf_source=conf_path)

# This example shows how to access the catalog configuration.
conf_catalog = conf_loader["catalog"]
```
