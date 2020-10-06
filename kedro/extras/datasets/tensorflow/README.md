# ImageDataGeneratorDataSet

`ImageDataGeneratorDataSet` relies on the 
[`tf.keras.preprocessing.ImageDataGenerator`](https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator) to create an image data generator for a local dataset.

`tf.keras.preprocessing.ImageDataGenerator` provides different methods to create image data generators
of which the following are implemented:

- [`flow`](https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator#flow) (not implemented)
- [`flow_from_directory`](https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator#flow_from_directory)
- [`flow_from_dataframe`](https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator#flow_from_dataframe) (not implemented)
- ...

Creating a `tf.keras.preprocessing.ImageDataGenerator` is usually followed using one of the above
methods. To do this with kedro in one of your nodes there exist additional datasets.
For example to make use of `flow_from_directory` use `FlowFromDirectoryDataSet`, 
see the [example](#example-use) below.


The [convention of `keras`](https://keras.io/api/preprocessing/image/) is to have the dataset 
stored in a folder structure according to (image names don't have to follow this convention):

```console
data_directory/
...class_a/
......a_image_1.jpg
......a_image_2.jpg
...class_b/
......b_image_1.jpg
......b_image_2.jpg
```

Note: Datasets stored in cloud locations such as `s3` and `gcs` are not supported by 
`tf.keras.preprocessing.ImageDataGenerator.flow_from_directory`.

## Example Use

```python
import tensorflow as tf

from kedro.extras.datasets.tensorflow import FlowFromDirectoryDataSet

# Make use of tf.keras.preprocessing.ImageDataGenerator.flow_from_directory
# to create generators for training and validation
rescale = 1./255
validation_split = 0.2
generator_args={
  rescale=rescale,
  validation_split=validation_split,
}

train_generator = FlowFromDirectoryDataSet(
                              generator_args=generator_args,
                              load_args={
                                directory="/local/path/to/images/train_data_dir",
                                subset='training'
                              })

validation_generator = FlowFromDirectoryDataSet(
                              generator_args=generator_args,
                              load_args={
                                directory="/local/path/to/images/validation_data_dir",
                                subset='validation'
                              })


model = tf.keras.Model()
model.fit(
        x=train_generator,
        epochs=50,
        validation_data=validation_generator)
```

## Example catalog.yaml

```yaml
train_data:
  type: tensorflow.FlowFromDirectoryDataSet
  generator_args: # If values are the same for train and validation use global generator_args
    rescale: 1./255
    validation_split: 0.2 
  load_args:
    directory: /local/path/to/images/train_data_dir

validation_data:
  type: tensorflow.FlowFromDirectoryDataSet
  generator_args: # If values are the same for train and validation use global generator_args
    rescale: 1./255
    validation_split: 0.2 
  load_args:
    directory: /local/path/to/images/validation_data_dir
```

Contributed by (fjp)[https://github.com/fjp].


# TensorFlowModelDataset

``TensorflowModelDataset`` loads and saves TensorFlow models.
The underlying functionality is supported by, and passes input arguments to TensorFlow 2.X load_model and save_model methods. Only TF2 is currently supported for saving and loading, V1 requires HDF5 and serializes differently.

#### Example use:
```python
import numpy as np
import tensorflow as tf

from kedro.extras.datasets.tensorflow import TensorFlowModelDataset

data_set = TensorFlowModelDataset("tf_model_dirname")

model = tf.keras.Model()
predictions = model.predict([...])

data_set.save(model)
loaded_model = data_set.load()

new_predictions = loaded_model.predict([...])
np.testing.assert_allclose(predictions, new_predictions, rtol=1e-6, atol=1e-6)
```

#### Example catalog.yml:
```yaml
example_tensorflow_data:
  type: tensorflow.TensorFlowModelDataset
  filepath: data/08_reporting/tf_model_dirname
```

Contributed by (Aleks Hughes)[https://github.com/w0rdsm1th].
