# Advanced: Tutorial to create a custom dataset

[Kedro supports several datasets](https://docs.kedro.org/projects/kedro-datasets/en/stable/) out of the box, but you may find that you need to create a custom dataset. For example, you may need to handle a proprietary data format or filesystem in your pipeline, or perhaps you have found a particular use case for a dataset that Kedro does not support. This tutorial explains how to create a custom dataset to read and save image data.

## Understand `AbstractDataset`

If you are a contributor and would like to submit a new dataset, extend the [kedro.io.AbstractDataset][] interface, or [kedro.io.AbstractVersionedDataset][] if you plan to support versioning. Subclasses must provide concrete `load` and `save` methods with consistent error handling wrappers. They also override `_describe`, which logs internal information about each instance of your custom `AbstractDataset`.


## Scenario

In this example, we use a [Kaggle dataset of Pokémon images and types](https://www.kaggle.com/datasets/vishalsubbiah/pokemon-images-and-types/). The goal is to train a model that classifies each [Pokémon](https://en.wikipedia.org/wiki/Pok%C3%A9mon)—for example, Water, Fire, or Bug—based on its appearance. To train the model, we read the Pokémon images from PNG files into `numpy` arrays before further manipulation in the Kedro pipeline. To work with PNG images out of the box, in this example we create an `ImageDataset` to read and save image data.

## Project setup

We assume that you have already [installed Kedro](../getting-started/install.md). Now [create a project](../create/new_project.md) (feel free to name your project as you like, but here we will assume the project's repository name is `kedro-pokemon`).

Log into your Kaggle account to [download the Pokémon dataset](https://www.kaggle.com/datasets/vishalsubbiah/pokemon-images-and-types) and unzip it into `data/01_raw`, within a subdirectory named `pokemon-images-and-types`. The data comprises a single `pokemon.csv` file plus a subdirectory of images.

The dataset will use [Pillow](https://pillow.readthedocs.io/en/stable/) for generic image processing functionality, to ensure that it can work with a range of different image formats, not limited to PNG.

To install Pillow:

```bash
pip install Pillow
```

Consult the [Pillow documentation](https://pillow.readthedocs.io/en/stable/installation.html) if you experience problems with the installation.

## The anatomy of a dataset

At the minimum, a valid Kedro dataset needs to subclass the base [kedro.io.AbstractDataset][] and provide an implementation for the following abstract methods:

* `load`
* `save`
* `_describe`

`AbstractDataset` is generically typed with an input data type for saving data, and an output data type for loading data.
This typing is optional and defaults to the `Any` type.

The `_EPHEMERAL` Boolean attribute in `AbstractDataset` indicates if a dataset is persistent. For example, for [kedro.io.MemoryDataset][], which is not persistent, it is set to True. By default, `_EPHEMERAL` is set to False.

!!! note
    Name the parameter that specifies the location of the data file or folder `filename`, `filepath`, or `path` in the constructor of the custom dataset class. This keeps dataset constructors consistent with the Kedro convention.

Here is an example skeleton for `ImageDataset`:

<!-- vale off -->
??? example "View code"
    ```python
    from typing import Any, Dict

    import numpy as np

    from kedro.io import AbstractDataset


    class ImageDataset(AbstractDataset[np.ndarray, np.ndarray]):
        """``ImageDataset`` loads / save image data from a given filepath as `numpy` array using Pillow.

        Example:
        ::

            >>> ImageDataset(filepath='/img/file/path.png')
        """

        def __init__(self, filepath: str):
            """Creates a new instance of ImageDataset to load / save image data at the given filepath.

            Args:
                filepath: The location of the image file to load / save data.
            """
            self._filepath = filepath

        def load(self) -> np.ndarray:
            """Loads data from the image file.

            Returns:
                Data from the image file as a numpy array.
            """
            ...

        def save(self, data: np.ndarray) -> None:
            """Saves image data to the specified filepath"""
            ...

        def _describe(self) -> Dict[str, Any]:
            """Returns a dict that describes the attributes of the dataset"""
            ...
    ```
<!-- vale on -->

Create a subdirectory called `datasets` in `src/kedro_pokemon/` to store the dataset definition `image_dataset.py`, adding `__init__.py` to make Python treat the directory as a package that you can import from:

```
src/kedro_pokemon/datasets
├── __init__.py
└── image_dataset.py
```

## Implement the `load` method with `fsspec`

Several built-in Kedro datasets rely on [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) as a consistent interface to different data sources, as described earlier in the section about the [Data Catalog](../catalog-data/data_catalog.md#dataset-filepath). In this example, using `fsspec` with `Pillow` keeps the dataset flexible across different image locations and formats.

Here is the implementation of the `load` method using `fsspec` and `Pillow` to read the data of a single image into a `numpy` array:

<!-- vale off -->
??? example "View code"
    ```python
    from pathlib import PurePosixPath
    from typing import Any, Dict

    import fsspec
    import numpy as np
    from PIL import Image

    from kedro.io import AbstractDataset
    from kedro.io.core import get_filepath_str, get_protocol_and_path


    class ImageDataset(AbstractDataset[np.ndarray, np.ndarray]):
        def __init__(self, filepath: str):
            """Creates a new instance of ImageDataset to load / save image data for given filepath.

            Args:
                filepath: The location of the image file to load / save data.
            """
            # parse the path and protocol (for example, file, http, s3, and similar schemes)
            protocol, path = get_protocol_and_path(filepath)
            self._protocol = protocol
            self._filepath = PurePosixPath(path)
            self._fs = fsspec.filesystem(self._protocol)

        def load(self) -> np.ndarray:
            """Loads data from the image file.

            Returns:
                Data from the image file as a numpy array
            """
            # using get_filepath_str ensures that the protocol and path are appended properly for different filesystems
            load_path = get_filepath_str(self._filepath, self._protocol)
            with self._fs.open(load_path) as f:
                image = Image.open(f).convert("RGBA")
                return np.asarray(image)

        ...
    ```
<!-- vale on -->

To test this out, add a dataset to the data catalog to load the image of Pikachu.

<!-- vale off -->
```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.datasets.image_dataset.ImageDataset
  filepath: data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  # Note: the duplicated `images` path is part of the original Kaggle dataset
```
<!-- vale on -->

Then launch an IPython session with `kedro ipython` to preview the data:

```
# read data image into a numpy array
In [1]: image = context.catalog.load('pikachu')

# then re-show the image using Pillow's Image API.
In [2]: from PIL import Image
In [3]: Image.fromarray(image).show()
```

## Implement the `save` method with `fsspec`

Similarly, define the `_save` method as follows:


```python
class ImageDataset(AbstractDataset[np.ndarray, np.ndarray]):
    def save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath."""
        # using get_filepath_str ensures that the protocol and path are appended properly for different filesystems
        save_path = get_filepath_str(self._filepath, self._protocol)
        with self._fs.open(save_path, "wb") as f:
            image = Image.fromarray(data)
            image.save(f)
```

Let's try it out in IPython:

```
In [1]: image = context.catalog.load('pikachu')
In [2]: context.catalog.save('pikachu', data=image)
```

You can open the file to verify that the data was written back as expected.

## Implement the `_describe` method

The `_describe` method is used for printing purposes. The convention in Kedro is for the method to return a dictionary describing the attributes of the dataset.

```python
class ImageDataset(AbstractDataset[np.ndarray, np.ndarray]):
    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset."""
        return dict(filepath=self._filepath, protocol=self._protocol)
```

## The complete example

Here is the full implementation of our basic `ImageDataset`:

<!-- vale off -->
??? example "View code"
    ```python
    from pathlib import PurePosixPath
    from typing import Any, Dict

    import fsspec
    import numpy as np
    from PIL import Image

    from kedro.io import AbstractDataset
    from kedro.io.core import get_filepath_str, get_protocol_and_path


    class ImageDataset(AbstractDataset[np.ndarray, np.ndarray]):
        """``ImageDataset`` loads / save image data from a given filepath as `numpy` array using Pillow.

        Example:
        ::

            >>> ImageDataset(filepath='/img/file/path.png')
        """

        def __init__(self, filepath: str):
            """Creates a new instance of ImageDataset to load / save image data for given filepath.

            Args:
                filepath: The location of the image file to load / save data.
            """
            protocol, path = get_protocol_and_path(filepath)
            self._protocol = protocol
            self._filepath = PurePosixPath(path)
            self._fs = fsspec.filesystem(self._protocol)

        def load(self) -> np.ndarray:
            """Loads data from the image file.

            Returns:
                Data from the image file as a numpy array
            """
            load_path = get_filepath_str(self._filepath, self._protocol)
            with self._fs.open(load_path, mode="r") as f:
                image = Image.open(f).convert("RGBA")
                return np.asarray(image)

        def save(self, data: np.ndarray) -> None:
            """Saves image data to the specified filepath."""
            save_path = get_filepath_str(self._filepath, self._protocol)
            with self._fs.open(save_path, mode="wb") as f:
                image = Image.fromarray(data)
                image.save(f)

        def _describe(self) -> Dict[str, Any]:
            """Returns a dict that describes the attributes of the dataset."""
            return dict(filepath=self._filepath, protocol=self._protocol)
    ```
<!-- vale on -->

## Integration with `PartitionedDataset`

At this stage, the `ImageDataset` handles a single image, but this example needs to load every Pokémon image from the raw data directory for further processing.

Kedro's [PartitionedDataset](https://docs.kedro.org/projects/kedro-datasets/en/feature-8.0/api/kedro_datasets/partitions.PartitionedDataset/) is a convenient way to load multiple separate data files of the same underlying dataset type into a directory.

To use `PartitionedDataset` with `ImageDataset` to load all Pokemon PNG images, add this to the data catalog YAML so that `PartitionedDataset` loads all PNG files from the data directory using `ImageDataset`:

```yaml
# in conf/base/catalog.yml

pokemon:
  type: partitions.PartitionedDataset
  dataset: kedro_pokemon.datasets.image_dataset.ImageDataset
  path: data/01_raw/pokemon-images-and-types/images/images
  filename_suffix: ".png"
```

Let's try it out in the IPython console:

```
In [1]: images = context.catalog.load('pokemon')
In [2]: len(images)
Out[2]: 721
```

Verify the number of `.png` files in the data directory (it should be `721`):

```console
$ ls -la data/01_raw/pokemon-images-and-types/images/images/*.png | wc -l
    721
```

## Versioning

### How to add versioning to your dataset

!!! note
    Versioning doesn't work with `PartitionedDataset`. You can't use both of them at the same time.

To add versioning support to the new dataset we need to extend the
 [kedro.io.AbstractVersionedDataset][] to:

* Accept a `version` keyword argument as part of the constructor
* Adapt the `load` and `save` method to use the versioned data path obtained from `_get_load_path` and `_get_save_path` respectively

The following amends the full implementation of our basic `ImageDataset`. It now loads and saves data to and from a versioned subdirectory (`data/01_raw/pokemon-images-and-types/images/images/pikachu.png/<version>/pikachu.png` with `version` being a datetime-formatted string `YYYY-MM-DDThh.mm.ss.sssZ` by default):


<!-- vale off -->
??? example "View code"
    ```python
    from pathlib import PurePosixPath
    from typing import Any, Dict

    import fsspec
    import numpy as np
    from PIL import Image

    from kedro.io import AbstractVersionedDataset
    from kedro.io.core import get_filepath_str, get_protocol_and_path, Version


    class ImageDataset(AbstractVersionedDataset[np.ndarray, np.ndarray]):
        """``ImageDataset`` loads / save image data from a given filepath as `numpy` array using Pillow.

        Example:
        ::

            >>> ImageDataset(filepath='/img/file/path.png')
        """

        def __init__(self, filepath: str, version: Version = None):
            """Creates a new instance of ImageDataset to load / save image data for given filepath.

            Args:
                filepath: The location of the image file to load / save data.
                version: The version of the dataset being saved and loaded.
            """
            protocol, path = get_protocol_and_path(filepath)
            self._protocol = protocol
            self._fs = fsspec.filesystem(self._protocol)

            super().__init__(
                filepath=PurePosixPath(path),
                version=version,
                exists_function=self._fs.exists,
                glob_function=self._fs.glob,
            )

        def load(self) -> np.ndarray:
            """Loads data from the image file.

            Returns:
                Data from the image file as a numpy array
            """
            load_path = get_filepath_str(self._get_load_path(), self._protocol)
            with self._fs.open(load_path, mode="r") as f:
                image = Image.open(f).convert("RGBA")
                return np.asarray(image)

        def save(self, data: np.ndarray) -> None:
            """Saves image data to the specified filepath."""
            save_path = get_filepath_str(self._get_save_path(), self._protocol)
            with self._fs.open(save_path, mode="wb") as f:
                image = Image.fromarray(data)
                image.save(f)

        def _describe(self) -> Dict[str, Any]:
            """Returns a dict that describes the attributes of the dataset."""
            return dict(
                filepath=self._filepath, version=self._version, protocol=self._protocol
            )
    ```
<!-- vale on -->
<!-- vale on -->

All versioned datasets automatically inherit a `list_versions()` method from `AbstractVersionedDataset` that allows you to retrieve all available versions of the dataset. This can be useful for tracking dataset history or implementing custom version selection logic.

The difference between the original `ImageDataset` and the versioned `ImageDataset` is as follows:

<!-- Generated by saving the original and versioned examples to a file and running `diff original.py versioned.py -U -1` -->
<!-- vale off -->
??? example "View code"
    ```diff
    from pathlib import PurePosixPath
    from typing import Any, Dict

    import fsspec
    import numpy as np
    from PIL import Image

    -from kedro.io import AbstractDataset
    -from kedro.io.core import get_filepath_str, get_protocol_and_path
    +from kedro.io import AbstractVersionedDataset
    +from kedro.io.core import get_filepath_str, get_protocol_and_path, Version


    -class ImageDataset(AbstractDataset[np.ndarray, np.ndarray]):
    +class ImageDataset(AbstractVersionedDataset[np.ndarray, np.ndarray]):
        """``ImageDataset`` loads / save image data from a given filepath as `numpy` array using Pillow.

        Example:
        ::

            >>> ImageDataset(filepath='/img/file/path.png')
        """

    -    def __init__(self, filepath: str):
    +    def __init__(self, filepath: str, version: Version = None):
            """Creates a new instance of ImageDataset to load / save image data for given filepath.

            Args:
                filepath: The location of the image file to load / save data.
    +            version: The version of the dataset being saved and loaded.
            """
            protocol, path = get_protocol_and_path(filepath)
            self._protocol = protocol
    -        self._filepath = PurePosixPath(path)
            self._fs = fsspec.filesystem(self._protocol)

    +        super().__init__(
    +            filepath=PurePosixPath(path),
    +            version=version,
    +            exists_function=self._fs.exists,
    +            glob_function=self._fs.glob,
    +        )
    +
        def load(self) -> np.ndarray:
            """Loads data from the image file.

            Returns:
                Data from the image file as a numpy array
            """
    -        load_path = get_filepath_str(self._filepath, self._protocol)
    +        load_path = get_filepath_str(self._get_load_path(), self._protocol)
            with self._fs.open(load_path, mode="r") as f:
                image = Image.open(f).convert("RGBA")
                return np.asarray(image)

        def save(self, data: np.ndarray) -> None:
            """Saves image data to the specified filepath."""
    -        save_path = get_filepath_str(self._filepath, self._protocol)
    +        save_path = get_filepath_str(self._get_save_path(), self._protocol)
            with self._fs.open(save_path, mode="wb") as f:
                image = Image.fromarray(data)
                image.save(f)

        def _describe(self) -> Dict[str, Any]:
            """Returns a dict that describes the attributes of the dataset."""
    -        return dict(filepath=self._filepath, protocol=self._protocol)
    +        return dict(
    +            filepath=self._filepath, version=self._version, protocol=self._protocol
    +        )
    ```
<!-- vale on -->

To test the code, you need to enable versioning support in the data catalog:

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.datasets.image_dataset.ImageDataset
  filepath: data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  versioned: true
```

!!! note
    Using an HTTP(S)-based `filepath` with `versioned: true` is NOT supported.

Create an initial version of the data by creating an example first version (for example, `2020-02-22T00.00.00.000Z`):

```console
$ mv data/01_raw/pokemon-images-and-types/images/images/pikachu.png data/01_raw/pokemon-images-and-types/images/images/pikachu.png.backup
$ mkdir -p data/01_raw/pokemon-images-and-types/images/images/pikachu.png/2020-02-22T00.00.00.000Z/
$ mv data/01_raw/pokemon-images-and-types/images/images/pikachu.png.backup data/01_raw/pokemon-images-and-types/images/images/pikachu.png/2020-02-22T00.00.00.000Z/pikachu.png
```

The directory structure should look like the following:

```
data/01_raw/pokemon-images-and-types/images/images/pikachu.png
└── 2020-02-22T00.00.00.000Z/
    └── pikachu.png
```

Launch an IPython shell to test load/save of the versioned data:

```
# loading works as Kedro automatically find the latest available version inside `pikachu.png` directory
In [1]: img = context.catalog.load('pikachu')
# then saving it should work as well
In [2]: context.catalog.save('pikachu', data=img)
```

Inspect the content of the data directory to find a new version of the data, written by `save`.


## Thread-safety

Kedro datasets should work with the [kedro.runner.SequentialRunner][] and the [kedro.runner.ParallelRunner][], so they must be fully serialisable by the [Python multiprocessing package](https://docs.python.org/3/library/multiprocessing.html). This means that your datasets should not make use of lambda functions, nested functions, closures etc. If you are using custom decorators, you need to ensure that they are using [`functools.wraps()`](https://docs.python.org/3/library/functools.html#functools.wraps).

[SparkDataset](https://docs.kedro.org/projects/kedro-datasets/en/feature-8.0/api/kedro_datasets/spark.SparkDataset/) is one exception.
[Apache Spark](https://spark.apache.org/) uses its own parallelism, so it doesn't work with Kedro [kedro.runner.ParallelRunner][].
For parallelism within a Kedro project that uses Spark, use [kedro.runner.ThreadRunner][] instead.

To verify whether your dataset is serialisable by `multiprocessing`, use the console or an IPython session to try dumping it using `multiprocessing.reduction.ForkingPickler`:

```python
dataset = context.catalog._datasets["pokemon"]
from multiprocessing.reduction import ForkingPickler

# the following call shouldn't throw any errors
ForkingPickler.dumps(dataset)
```

## How to handle credentials and different filesystems

If your use case requires them, Kedro allows you to pass `credentials` and filesystem-specific `fs_args` parameters to your dataset. For example, if the Pokémon data sits in an S3 bucket, we can add the `credentials` and `fs_args` to the data catalog as follows:

<!-- vale off -->
```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.datasets.image_dataset.ImageDataset
  filepath: s3://data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  credentials: <your_credentials>
  fs_args:
    arg_1: <value>
```
<!-- vale on -->

These parameters are then passed to the dataset constructor so you can use them with `fsspec`:

```python
import fsspec


class ImageDataset(AbstractVersionedDataset):
    def __init__(
        self,
        filepath: str,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ):
        """Creates a new instance of ImageDataset to load / save image data for given filepath.

        Args:
            filepath: The location of the image file to load / save data.
            version: The version of the dataset being saved and loaded.
            credentials: Credentials required to get access to the underlying filesystem.
                For example, for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Extra arguments to pass into underlying filesystem class.
                For example, for ``GCSFileSystem`` class: `{"project": "my-project", ...}`.
        """
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **credentials, **fs_args)

    ...
```

We provide additional examples of [how to use parameters through the data catalog's YAML API](../catalog-data/data_catalog_yaml_examples.md). For an example of how to use these parameters in your dataset constructor, see the implementation of the [SparkDataset](https://docs.kedro.org/projects/kedro-datasets/en/feature-8.0/api/kedro_datasets/spark.SparkDataset/).

## How to contribute a custom dataset implementation

One of the easiest ways to contribute back to Kedro is to share a custom dataset. Kedro has a `kedro-datasets` package in the [`kedro-plugins` repository](https://github.com/kedro-org/kedro-plugins), where you can add a new custom dataset implementation to share with others. You can find more information in the [Kedro contribution guide on GitHub](https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md).

To contribute your custom dataset:
1. Add your dataset package to `kedro-plugins/kedro-datasets/kedro_datasets/`.

For example, in our `ImageDataset` example, the directory structure should be:

```
kedro-plugins/kedro-datasets/kedro_datasets/image
├── __init__.py
└── image_dataset.py
```

2. If the dataset is complex, create a `README.md` file to explain how it works and document its API.
3. Core datasets should be accompanied by full test coverage in `kedro-plugins/kedro-datasets/tests/`.
4. Datasets should also be added to the documentation.
    To ensure your dataset appears properly in the documentation you need to:

    1. Ensure your dataset class has a markdown-parseable docstring.
    2. Add an entry to the table in `index.md` within either:
        - `docs/pages/api/kedro_datasets/` (for core datasets), or
        - `docs/pages/api/kedro_datasets_experimental/` (for experimental datasets).
    3. Create a markdown file for your dataset in the corresponding directory.
    4. Add the dataset markdown file to the navigation section of `mkdocs.yml`.

5. Make a pull request against the `main` branch of the [Kedro plugins repository](https://github.com/kedro-org/kedro-plugins).

!!! info
    There are two types of datasets you can contribute: **core** and **experimental**.

    - **Core datasets** are officially maintained by the Kedro Technical Steering Committee (TSC) and must meet high standards, including full documentation, 100% test coverage, cross-platform support, and compatibility with supported Python versions.
    - **Experimental datasets** are community-contributed and more flexible. They are not officially maintained and can be in early stages or less thoroughly tested.

    Read the full details about the dataset types and what the contribution process is for each in [the `kedro-dataset` contribution guide](https://github.com/kedro-org/kedro-plugins/blob/75c553b/kedro-datasets/CONTRIBUTING.md).
