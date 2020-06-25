# Install Kedro

We recommend installing Kedro in a [new virtual environment](01_prerequisites.md#working-with-virtual-environments) for *each* of your projects.

To install Kedro from the Python Package Index (PyPI) simply run:

```bash
pip install kedro
```

It is also possible to install Kedro using `conda`, a package and environment manager program bundled with [Anaconda](01_prerequisites.md#working-with-virtual-environments), using:

```bash
conda install -c conda-forge kedro
```

Both approaches install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

## Verify a successful installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [FAQs](../06_resources/01_faq.md) for help.

## Install a development version

You can try out a development version of Kedro direct from the [repository](https://github.com/quantumblacklabs/kedro) by following [these steps](../06_resources/01_faq.md#how-can-i-use-development-version-of-kedro).
