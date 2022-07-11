# Custom datasets

[Kedro supports many datasets](/kedro.extras.datasets) out of the box, but you may find that you need to create a custom dataset. For example, you may need to handle a proprietary data format or filesystem in your pipeline, or perhaps you have found a particular use case for a dataset that Kedro does not support. This tutorial explains how to create a custom dataset to read and save image data.

## Scenario

In this example, we use a [Kaggle dataset of Pokémon images and types](https://www.kaggle.com/vishalsubbiah/pokemon-images-and-types) to train a model to classify the type of a given [Pokémon](https://en.wikipedia.org/wiki/Pok%C3%A9mon), e.g. Water, Fire, Bug, etc., based on its appearance. To train the model, we read the Pokémon images from PNG files into `numpy` arrays before further manipulation in the Kedro pipeline. To work with PNG images out of the box, in this example we create an `ImageDataSet` to read and save image data.

## Project setup

We assume that you have already [installed Kedro](../get_started/install.md). Now [create a project](../get_started/new_project.md) (feel free to name your project as you like, but here we will assume the project's repository name is `kedro-pokemon`).

Log into your Kaggle account to [download the Pokémon dataset](https://www.kaggle.com/vishalsubbiah/pokemon-images-and-types) and unzip it into `data/01_raw`, within a subfolder named `pokemon-images-and-types`. The data comprises a single `pokemon.csv` file plus a subfolder of images.

The dataset will use [Pillow](https://pillow.readthedocs.io/en/stable/) for generic image processing functionality, to ensure that it can work with a range of different image formats, not just PNG.

To install Pillow:

```bash
pip install Pillow
```

Consult the [Pillow documentation](https://pillow.readthedocs.io/en/stable/installation.html) if you experience problems with the installation.

## The anatomy of a dataset

At the minimum, a valid Kedro dataset needs to subclass the base [AbstractDataSet](/kedro.io.AbstractDataSet) and provide an implementation for the following abstract methods:

* `_load`
* `_save`
* `_describe`

`AbstractDataSet` is generically typed with an input data type for saving data, and an output data type for loading data.
This typing is optional however, and defaults to `Any` type.

Here is an example skeleton for `ImageDataSet`:

<details>
<summary><b>Click to expand</b></summary>

```python
from typing import Any, Dict

import numpy as np

from kedro.io import AbstractDataSet


class ImageDataSet(AbstractDataSet[np.ndarray, np.ndarray]):
    """``ImageDataSet`` loads / save image data from a given filepath as `numpy` array using Pillow.

    Example:
    ::

        >>> ImageDataSet(filepath='/img/file/path.png')
    """

    def __init__(self, filepath: str):
        """Creates a new instance of ImageDataSet to load / save image data at the given filepath.

        Args:
            filepath: The location of the image file to load / save data.
        """
        self._filepath = filepath

    def _load(self) -> np.ndarray:
        """Loads data from the image file.

        Returns:
            Data from the image file as a numpy array.
        """
        ...

    def _save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath"""
        ...

    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset"""
        ...
```
</details>

Create a subfolder called `extras` in `src/kedro_pokemon/`, and a `datasets` subfolder within that, to store the dataset definition `image_dataset.py` and mimic the structure inside Kedro's own codebase (including `__init__.py` to make Python treat those directories containing the file as packages that you can import from):

```
src/kedro_pokemon/extras
├── __init__.py
└── datasets
    ├── __init__.py
    └── image_dataset.py
```

## Implement the `_load` method with `fsspec`

Many of the built-in Kedro datasets rely on [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) as a consistent interface to different data sources, as described earlier in the section about the [Data Catalog](../data/data_catalog.md#specify-the-location-of-the-dataset). In this example, it's particularly convenient to use `fsspec` in conjunction with `Pillow` to read image data, since it allows the dataset to work flexibly with different image locations and formats.

Here is the implementation of the `_load` method using `fsspec` and `Pillow` to read the data of a single image into a `numpy` array:

<details>
<summary><b>Click to expand</b></summary>

```python
from pathlib import PurePosixPath
from typing import Any, Dict

import fsspec
import numpy as np
from PIL import Image

from kedro.io import AbstractDataSet
from kedro.io.core import get_filepath_str, get_protocol_and_path


class ImageDataSet(AbstractDataSet[np.ndarray, np.ndarray]):
    def __init__(self, filepath: str):
        """Creates a new instance of ImageDataSet to load / save image data for given filepath.

        Args:
            filepath: The location of the image file to load / save data.
        """
        # parse the path and protocol (e.g. file, http, s3, etc.)
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = PurePosixPath(path)
        self._fs = fsspec.filesystem(self._protocol)

    def _load(self) -> np.ndarray:
        """Loads data from the image file.

        Returns:
            Data from the image file as a numpy array
        """
        # using get_filepath_str ensures that the protocol and path are appended correctly for different filesystems
        load_path = get_filepath_str(self._filepath, self._protocol)
        with self._fs.open(load_path) as f:
            image = Image.open(f).convert("RGBA")
            return np.asarray(image)

    ...
```
</details>

To test this out, let's add a dataset to the data catalog to load [Pikachu's](https://en.wikipedia.org/wiki/Pikachu) image.

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.extras.datasets.image_dataset.ImageDataSet
  filepath: data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  # Note: the duplicated `images` path is part of the original Kaggle dataset
```

Then launch an IPython session with `kedro ipython` to preview the data:

```
# read data image into a numpy array
In [1]: image = context.catalog.load('pikachu')

# then re-show the image using Pillow's Image API.
In [2]: from PIL import Image
In [3]: Image.fromarray(image).show()
```

## Implement the `_save` method with `fsspec`

Similarly, we can implement the `_save` method as follows:


```python
class ImageDataSet(AbstractDataSet[np.ndarray, np.ndarray]):
    def _save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath."""
        # using get_filepath_str ensures that the protocol and path are appended correctly for different filesystems
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

You can open the file to verify that the data was written back correctly.

## Implement the `_describe` method

The `_describe` method is used for printing purposes. The convention in Kedro is for the method to return a dictionary describing the attributes of the dataset.

```python
class ImageDataSet(AbstractDataSet[np.ndarray, np.ndarray]):
    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset."""
        return dict(filepath=self._filepath, protocol=self._protocol)
```

## The complete example

Here is the full implementation of our basic `ImageDataSet`:

<details>
<summary><b>Click to expand</b></summary>

```python
from pathlib import PurePosixPath
from typing import Any, Dict

import fsspec
import numpy as np
from PIL import Image

from kedro.io import AbstractDataSet
from kedro.io.core import get_filepath_str, get_protocol_and_path


class ImageDataSet(AbstractDataSet[np.ndarray, np.ndarray]):
    """``ImageDataSet`` loads / save image data from a given filepath as `numpy` array using Pillow.

    Example:
    ::

        >>> ImageDataSet(filepath='/img/file/path.png')
    """

    def __init__(self, filepath: str):
        """Creates a new instance of ImageDataSet to load / save image data for given filepath.

        Args:
            filepath: The location of the image file to load / save data.
        """
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = PurePosixPath(path)
        self._fs = fsspec.filesystem(self._protocol)

    def _load(self) -> np.ndarray:
        """Loads data from the image file.

        Returns:
            Data from the image file as a numpy array
        """
        load_path = get_filepath_str(self._filepath, self._protocol)
        with self._fs.open(load_path, mode="r") as f:
            image = Image.open(f).convert("RGBA")
            return np.asarray(image)

    def _save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath."""
        save_path = get_filepath_str(self._filepath, self._protocol)
        with self._fs.open(save_path, mode="wb") as f:
            image = Image.fromarray(data)
            image.save(f)

    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset."""
        return dict(filepath=self._filepath, protocol=self._protocol)
```
</details>

## Integration with `PartitionedDataSet`

Currently, the `ImageDataSet` only works with a single image, but this example needs to load all Pokemon images from the raw data directory for further processing.

Kedro's [`PartitionedDataSet`](../data/kedro_io.md#partitioned-dataset) is a convenient way to load multiple separate data files of the same underlying dataset type into a directory.

To use `PartitionedDataSet` with `ImageDataSet` to load all Pokemon PNG images, add this to the data catalog YAML so that `PartitionedDataSet` loads all PNG files from the data directory using `ImageDataSet`:

```yaml
# in conf/base/catalog.yml

pokemon:
  type: PartitionedDataSet
  dataset: kedro_pokemon.extras.datasets.image_dataset.ImageDataSet
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

```{note}
Versioning doesn't work with `PartitionedDataSet`. You can't use both of them at the same time.
```
To add [Versioning](../data/kedro_io.md#versioning) support to the new dataset we need to extend the
 [AbstractVersionedDataSet](/kedro.io.AbstractVersionedDataSet) to:

* Accept a `version` keyword argument as part of the constructor
* Adapt the `_save` and `_load` method to use the versioned data path obtained from `_get_save_path` and `_get_load_path` respectively

The following amends the full implementation of our basic `ImageDataSet`. It now loads and saves data to and from a versioned subfolder (`data/01_raw/pokemon-images-and-types/images/images/pikachu.png/<version>/pikachu.png` with `version` being a datetime-formatted string `YYYY-MM-DDThh.mm.ss.sssZ` by default):


<details>
<summary><b>Click to expand</b></summary>

```python
from pathlib import PurePosixPath
from typing import Any, Dict

import fsspec
import numpy as np
from PIL import Image

from kedro.io import AbstractVersionedDataSet
from kedro.io.core import get_filepath_str, get_protocol_and_path, Version


class ImageDataSet(AbstractVersionedDataSet[np.ndarray, np.ndarray]):
    """``ImageDataSet`` loads / save image data from a given filepath as `numpy` array using Pillow.

    Example:
    ::

        >>> ImageDataSet(filepath='/img/file/path.png')
    """

    def __init__(self, filepath: str, version: Version = None):
        """Creates a new instance of ImageDataSet to load / save image data for given filepath.

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

    def _load(self) -> np.ndarray:
        """Loads data from the image file.

        Returns:
            Data from the image file as a numpy array
        """
        load_path = get_filepath_str(self._get_load_path(), self._protocol)
        with self._fs.open(load_path, mode="r") as f:
            image = Image.open(f).convert("RGBA")
            return np.asarray(image)

    def _save(self, data: np.ndarray) -> None:
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
</details>

The difference between the original `ImageDataSet` and the versioned `ImageDataSet` is as follows:

<!-- Generated by saving the original and versioned examples to a file and running `diff original.py versioned.py -U -1` -->
<details>
<summary><b>Click to expand</b></summary>

```diff
 from pathlib import PurePosixPath
 from typing import Any, Dict

 import fsspec
 import numpy as np
 from PIL import Image

-from kedro.io import AbstractDataSet
-from kedro.io.core import get_filepath_str, get_protocol_and_path
+from kedro.io import AbstractVersionedDataSet
+from kedro.io.core import get_filepath_str, get_protocol_and_path, Version


-class ImageDataSet(AbstractDataSet[np.ndarray, np.ndarray]):
+class ImageDataSet(AbstractVersionedDataSet[np.ndarray, np.ndarray]):
     """``ImageDataSet`` loads / save image data from a given filepath as `numpy` array using Pillow.

     Example:
     ::

         >>> ImageDataSet(filepath='/img/file/path.png')
     """

-    def __init__(self, filepath: str):
+    def __init__(self, filepath: str, version: Version = None):
         """Creates a new instance of ImageDataSet to load / save image data for given filepath.

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
     def _load(self) -> np.ndarray:
         """Loads data from the image file.

         Returns:
             Data from the image file as a numpy array
         """
-        load_path = get_filepath_str(self._filepath, self._protocol)
+        load_path = get_filepath_str(self._get_load_path(), self._protocol)
         with self._fs.open(load_path, mode="r") as f:
             image = Image.open(f).convert("RGBA")
             return np.asarray(image)

     def _save(self, data: np.ndarray) -> None:
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
</details>

To test the code, you need to enable versioning support in the data catalog:

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.extras.datasets.image_dataset.ImageDataSet
  filepath: data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  versioned: true
```

```{note}
Using an HTTP(S)-based `filepath` with `versioned: true` is NOT supported.
```

Create an initial version of the data by creating an example first version (e.g. `2020-02-22T00.00.00.000Z`):

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

You may also want to consult the [in-depth documentation about the Versioning API](../data/kedro_io.md#versioning).

## Thread-safety

Kedro datasets should work with the [SequentialRunner](/kedro.runner.SequentialRunner) and the [ParallelRunner](/kedro.runner.ParallelRunner), so they must be fully serialisable by the [Python multiprocessing package](https://docs.python.org/3/library/multiprocessing.html). This means that your datasets should not make use of lambda functions, nested functions, closures etc. If you are using custom decorators, you need to ensure that they are using [`functools.wraps()`](https://docs.python.org/3/library/functools.html#functools.wraps).

There is one dataset that is an exception: [SparkDataSet](/kedro.extras.datasets.spark.SparkDataSet). The explanation for this exception is that [Apache Spark](https://spark.apache.org/) uses its own parallelism and therefore doesn't work with Kedro [ParallelRunner](/kedro.runner.ParallelRunner). For parallelism within a Kedro project that leverages Spark please consider the alternative [ThreadRunner](/kedro.runner.ThreadRunner).

To verify whether your dataset is serialisable by `multiprocessing`, use the console or an iPython session to try dumping it using `multiprocessing.reduction.ForkingPickler`:

```python
dataset = context.catalog._data_sets["pokemon"]
from multiprocessing.reduction import ForkingPickler

# the following call shouldn't throw any errors
ForkingPickler.dumps(dataset)
```

## How to handle credentials and different filesystems

If your use case requires them, Kedro allows you to pass `credentials` and filesystem-specific `fs_args` parameters to your dataset. For example, if the Pokémon data sits in an S3 bucket, we can add the `credentials` and `fs_args` to the data catalog as follows:

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.extras.datasets.image_dataset.ImageDataSet
  filepath: s3://data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  credentials: <your_credentials>
  fs_args:
    arg_1: <value>
```

These parameters are then passed to the dataset constructor so you can use them with `fsspec`:

```python
import fsspec


class ImageDataSet(AbstractVersionedDataSet):
    def __init__(
        self,
        filepath: str,
        version: Version = None,
        credentials: Dict[str, Any] = None,
        fs_args: Dict[str, Any] = None,
    ):
        """Creates a new instance of ImageDataSet to load / save image data for given filepath.

        Args:
            filepath: The location of the image file to load / save data.
            version: The version of the dataset being saved and loaded.
            credentials: Credentials required to get access to the underlying filesystem.
                E.g. for ``GCSFileSystem`` it should look like `{"token": None}`.
            fs_args: Extra arguments to pass into underlying filesystem class.
                E.g. for ``GCSFileSystem`` class: `{"project": "my-project", ...}`.
        """
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._fs = fsspec.filesystem(self._protocol, **credentials, **fs_args)

    ...
```

We provide additional examples of [how to use parameters through the data catalog's YAML API](../data/data_catalog.md#use-the-data-catalog-with-the-yaml-api). For an example of how to use these parameters in your dataset's constructor, please see the [SparkDataSet](/kedro.extras.datasets.spark.SparkDataSet)'s implementation.


## How to contribute a custom dataset implementation

One of the easiest ways to contribute back to Kedro is to share a custom dataset. Kedro has a :code:`kedro.extras.datasets` sub-package where you can add a new custom dataset implementation to share it with others. You can find out more in the [Kedro contribution guide on GitHub](https://github.com/kedro-org/kedro/blob/main/CONTRIBUTING.md).

To contribute your custom dataset:

1. Add your dataset package to `kedro/extras/datasets/`.

For example, in our `ImageDataSet` example, the directory structure should be:

```
kedro/extras/datasets/image
├── __init__.py
└── image_dataset.py
```

2. If the dataset is complex, create a `README.md` file to explain how it works and document its API.

3. The dataset should be accompanied by full test coverage in `tests/extras/datasets`.

4. Make a pull request against the `main` branch of [Kedro's Github repository](https://github.com/kedro-org/kedro).
