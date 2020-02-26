# Creating a new dataset

Even though Kedro supports many [datasets](/kedro.extras.datasets) out of the box to help you with your IO need, sometimes they are not enough. For example, you might be dealing with a particular proprietary data format or filesystem in your pipeline, or perhaps you have found a popular use-case for dataset that isn't supported by Kedro yet and want to contribute. This tutorial will help you understand what's involved in the process of creating a new dataset and contributing it to Kedro.

## Scenario

Suppose we are training a model to classify the type of a [Pokémon](https://en.wikipedia.org/wiki/Pok%C3%A9mon), e.g. Water, Fire, Bug, etc., based on its appearance. We will be using this [Kaggle dataset](https://www.kaggle.com/vishalsubbiah/pokemon-images-and-types), which contains ~2MB of Pokémon images as well as a CSV containing their corresponding types.

## Project setup

Let's bootstrap our project with `kedro new` and name our project `kedro-pokemon`. Then download and save the dataset in `data/01_raw`. The `data` directory structure should be:

```
data
├── 01_raw
│   └── pokemon-images-and-types
├── 02_intermediate
├── 03_primary
├── 04_features
├── 05_model_input
├── 06_models
├── 07_model_output
└── 08_reporting
```

## Problem

In order to train our model, we will need a mechanism to read the Pokémon images from `png` files into `numpy` arrays for further manipulation in our Kedro pipeline. As Kedro doesn't provide a dataset to work with PNG images out of the box, this is a good opportunity to create an `ImageDataSet` to facilitate the reading and saving of image data in our project. The dataset will use [Pillow](https://pillow.readthedocs.io/en/stable/) under the hood for generic image processing functionality so that it will work with many different image formats, not just PNG.

To install Pillow:

```console
$ pip install Pillow
```

If you run into any installation problem, please head over to their [documentation](https://pillow.readthedocs.io/en/stable/installation.html) for more details.

## The anatomy of a dataset

At the minimum, a valid Kedro dataset needs to subclass the base [AbstractDataSet](/kedro.io.AbstractDataSet) and provide an implementation for the `_load`, `_save` and `_describe` abstract methods. For example, a skeleton for our `ImageDataSet` might look like:

```python
from typing import Any, Dict, List

import numpy as np

from kedro.io import AbstractDataSet


class ImageDataSet(AbstractDataSet):
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

We can place this dataset definition in `src/kedro_pokemon/io/datasets/image_dataset.py` to mimic the structure inside the Kedro's codebase:

```
src/kedro_pokemon/io
├── __init__.py
└── datasets
    ├── __init__.py
    └── image_dataset.py
```

## Implement the `_load` method with `fsspec`

Under the hood, a lot of Kedro built-in datasets rely on [fsspec](https://filesystem-spec.readthedocs.io/en/latest/) to interface with various different data sources in a consistent manner. More information could be found [here](./04_data_catalog.html#specifying-the-location-of-the-dataset). In our scenario, it's particularly convenient to use `fsspec` in conjunction with `Pillow` to read an image's data so that the dataset could work flexibly not just with different image formats but also with different image locations, such as S3, GCP, local filesystems, etc. Below is an implementation of the `_load` method using `fsspec` and `Pillow` to read the data of a single image in a `numpy` array:

```python
from pathlib import PurePosixPath

from kedro.io import AbstractDataSet
from kedro.io.core import get_filepath_str, get_protocol_and_path

import fsspec
import numpy as np

# PIL is the package from Pillow
from PIL import Image


class ImageDataSet(AbstractDataSet):
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
        load_path = get_filepath_str(self._get_load_path(), self._protocol)
        with self._fs.open(load_path) as f:
            image = Image.open(f).convert('RGBA')
            return np.asarray(image)
```

To test this out, let's add a dataset to the data catalog to load [Pikachu's](https://en.wikipedia.org/wiki/Pikachu) image.

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.io.datasets.image_dataset.ImageDataSet
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

Similarly, we can use implement our `_save` method as follows:

```python
import numpy as np
from PIL import Image
from kedro.io import AbstractDataSet
from kedro.io.core import get_filepath_str


class ImageDataSet(AbstractDataSet):
    def _save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath.
        """
        # using get_filepath_str ensures that the protocol and path are appended correctly for different filesystems
        save_path = get_filepath_str(self._get_save_path(), self._protocol)
        with self._fs.open(save_path, 'wb') as f:
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

The `_describe` method is used for printing purposes. The convention in Kedro is for the method to return a dictionary describing the attributes of the dataset .

```python
from kedro.io import AbstractDataSet


class ImageDataSet(AbstractDataSet):
    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset.
        """
        return dict(
            filepath=self._filepath,
            protocol=self._protocol
        )
```

## Bringing it all together

Here is the full implementation of our basic `ImageDataSet`:

```python
from pathlib import PurePosixPath
from typing import Any, Dict

from kedro.io import AbstractDataSet
from kedro.io.core import get_filepath_str, get_protocol_and_path

import fsspec
import numpy as np
from PIL import Image


class ImageDataSet(AbstractDataSet):
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
        load_path = get_filepath_str(self._get_load_path(), self._protocol)
        with self._fs.open(load_path, mode="r") as f:
            image = Image.open(f).convert('RGBA')
            return np.asarray(image)

    def _save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath.
        """
        # using get_filepath_str ensures that the protocol and path are appended correctly for different filesystems
        save_path = get_filepath_str(self._get_save_path(), self._protocol)
        with self._fs.open(save_path, mode="wb") as f:
            image = Image.fromarray(data)
            image.save(f)

    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset.
        """
        return dict(
            filepath=self._filepath,
            protocol=self._protocol
        )
```

## Integrating with `PartitionedDataSet`

A keen reader might have noticed that up until now our `ImageDataSet` only works with one single image. What about loading all Pokemon images from the raw data directory for further processing? The answer is using a [PartitionDataSet](./04_user_guide/08_advanced_io.html#partitioned-dataset).

`PartitionedDataSet` is a convenient way to load many separate data files of the same underlying dataset type in a directory. For example, in our Pokemon pipeline, to use `PartitionedDataSet` with our `ImageDataSet` to load all Pokemon PNG images, simply add this to the data catalog:

```yaml
pokemon:
  type: PartitionedDataSet
  dataset: kedro_pokemon.io.datasets.image_dataset.ImageDataSet
  path: data/01_raw/pokemon-images-and-types/images/images
  filename_suffix: ".png"
```

Let's try it out in the IPython console:

```
In [1]: images = context.catalog.load('pokemon')
In [2]: len(images)
Out[2]: 721
```

Verify the number of `.png` files in the data directory is indeed `721`:

```console
$ ls -la data/01_raw/pokemon-images-and-types/images/images/*.png | wc -l
    721
```

This proves that the `PartitionedDataSet` has helped us load all PNG files from the data directory using the underlying `ImageDataSet`. More importantly, we have enabled this capability just through updating a few lines of YAML. Pretty neat, right?

## Adding Versioning

> *Note*: Versioning doesn't work with PartitionedDataSet. You can't use both of them at the same time.

To add [Versioning](./04_user_guide/08_advanced_io.md#versioning) support to our dataset, at the minimum, we need to extend the [AbstractVersionedDataSet](/kedro.io.AbstractVersionedDataSet) to:

* Accept a `version` keyword argument as part of the constructor; and
* Adapt the `_save` and `_load` method to use the versioned data path obtained from `_get_save_path` and `_get_load_path` accordingly.

In our example, out of the box, the following implementation will load and save data to and from `data/01_raw/pokemon-images-and-types/images/images/pikachu.png/<version>/pikachu.png` with `version` being a datetime-formatted string `YYYY-MM-DDThh.mm.ss.sssZ` by default:


```python
from pathlib import PurePosixPath
from typing import Any, Dict

from kedro.io import AbstractVersionedDataSet, Version
from kedro.io.core import get_protocol_and_path

import fsspec
import numpy as np
from PIL import Image


class ImageDataSet(AbstractVersionedDataSet):
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
        load_path = self._get_load_path()
        with self._fs.open(load_path, mode="r") as f:
            image = Image.open(f).convert('RGBA')
            return np.asarray(image)

    def _save(self, data: np.ndarray) -> None:
        """Saves image data to the specified filepath.
        """
        save_path = self._get_save_path()
        with self._fs.open(save_path, mode="wb") as f:
            image = Image.fromarray(data)
            image.save(f)

    def _describe(self) -> Dict[str, Any]:
        """Returns a dict that describes the attributes of the dataset.
        """
        return dict(
            filepath=self._filepath,
            version=self._version,
            protocol=self._protocol
        )
```

To test it out, first enable versioning support in our data catalog:

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.io.datasets.image_dataset.ImageDataSet
  filepath: data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  versioned: true
```

> *Note*: Using an HTTP(S)-based `filepath` with `versioned: true` is NOT supported.

And create an initial version of the data by creating a `2020-02-22T00.00.00.000Z` directory as an example first version:

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

Then launch an IPython shell to try loading and saving versioned data:

```
# loading works as Kedro automatically find the latest available version inside `pikachu.png` directory
In [1]: img = context.catalog.load('pikachu')
# then saving it should work as well
In [2]: context.catalog.save('pikachu', data=img)
```

If you inspect the content of the data directory, you might notice that a new version of the data was written with the `save` call. Try calling `save` a few more times on your dataset and observe the change in the data directory. That's a versioned dataset in action. Visit [here](./04_user_guide/08_advanced_io.md#versioning) for a more in-depth documentation of the Versioning API.

## Thread-safety consideration

Every Kedro dataset should work with both the [SequentialRunner](/kedro.runner.SequentialRunner) as well as the [ParallelRunner](/kedro.runner.ParallelRunner). Therefore, it must be fully serialisable by Python's [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) package, i.e. data sets should not make use of lambda functions, nested functions, closures etc. If you are using custom decorators ensure they are using [`functools.wraps()`](https://docs.python.org/3/library/functools.html#functools.wraps).

To verify whether your dataset is serialisable by `multiprocessing`, try dumping it using `multiprocessing.reduction.ForkingPickler`:

```python
dataset = context.catalog._data_sets['pokemon']
from multiprocessing.reduction import ForkingPickler

# the following call shouldn't throw any errors
ForkingPickler.dumps(dataset)
```

## Handling credentials and different filesystems

Kedro allows you to pass `credentials` as well as filesystem-specific `fs_args` parameters to your dataset if your use-case requires them. For example, if the Pokémon data reside in an S3 bucket, we can add the `credentials` and `fs_args` to the data catalog as follows:

```yaml
# in conf/base/catalog.yml

pikachu:
  type: kedro_pokemon.io.datasets.image_dataset.ImageDataSet
  filepath: s3://data/01_raw/pokemon-images-and-types/images/images/pikachu.png
  credentials: <your_credentials>
  fs_args:
    arg_1: <value>
```

These parameters are then passed to the dataset constructor so you can use them accordingly with `fsspec`:

```python
import fsspec


class ImageDataSet(AbstractDataSet):
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
        self._fs = fsspec.filesystem(self._protocol, **_credentials, **_fs_args)
    ...
```

* For more examples on how to use these parameters through the data catalog's YAML API, please read [this user guide](./04_data_catalog.md#using-the-data-catalog-with-the-yaml-api).
* For an example implementation on how to use these parameters in your dataset's constructor, please see the [SparkDataSet](/kedro.extras.datasets.spark.SparkDataSet)'s implementation.

## Contribute your dataset to Kedro

After you are happy with how your new dataset behaves in your project, if you believe that it can benefit other members of the community, please do consider contributing your dataset to Kedro. The process is simple:

* Add your dataset package to `kedro/extras/datasets/`. For example, in our `ImageDataSet` example, the directory structure should be:

```
kedro/extras/datasets/image
├── __init__.py
└── image_dataset.py
```

* If the dataset is complicated, create a `README.md` file explaining how your dataset works as well as document its API is encouraged.
* The dataset should be accompanied by full tests coverage, located at `tests/extras/datasets` accordingly.
* Make a Pull Request against the `develop` branch in the [kedro](https://github.com/quantumblacklabs/kedro) repository. For more information, please read our [contributing](https://github.com/quantumblacklabs/kedro/blob/develop/CONTRIBUTING.md) guide.
