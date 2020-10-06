import tensorflow as tf 
from kedro.io.core import AbstractDataSet
from typing import Any, Dict

class ImageDataGeneratorDataSet(AbstractDataSet):

    def __init__(
        self,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None
    ) -> None:
        """Creates a new instance of `ImageDataGeneratorDataSet`
            to generate batches of tensor image data with real-time data augmentation.
            
            A `tf.keras.preprocessing.ImageDataGenerator` provides methods such as
            `flow` and `flow_from_directory`. 
            To use one of these Datasets see `kedro.extras.datasets.tensorflow.FlowFromDirectoryDataSet`
            See the following for more details of `tf.keras.preprocessing.ImageDataGenerator`:
            - https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator
            - https://keras.io/api/preprocessing/image/
            - https://blog.keras.io/building-powerful-image-classification-models-using-very-little-data.html

        Args:
            load_args: Optional arguments passed to `tf.keras.preprocessing.ImageDataGenerator`.
                Here you can find all available arguments:
                https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator
                All defaults are preserved.
        """
        self.load_args = load_args
        self.save_args = save_args 

    def _load(self):
        return tf.keras.preprocessing.image.ImageDataGenerator(**self.load_args)

    def _save(self, data):
        raise Exception("Saving with the ImageDataGeneratorDataSet is not supported")
    
    

class FlowFromDirectoryDataSet(AbstractDataSet):   
    def __init__(
        self,
        directory: str,
        generator_args: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None
    ) -> None:
        """Creates a new instance of `ImageDataGeneratorDataSet`.

        Args:
            directory: Local path to the target directory. 
                It should contain one subdirectory per class. Any PNG, JPG, BMP, PPM or TIF 
                images inside each of the subdirectories directory tree will be included in the 
                generator. See the following for details
                - https://keras.io/api/preprocessing/image/
                - https://blog.keras.io/building-powerful-image-classification-models-using-very-little-data.html
            generator_args: Optional arguments passed to `tf.keras.preprocessing.ImageDataGenerator`.
                Here you can find all available arguments:
                https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator
                All defaults are preserved.
            load_args: Optional arguments passed to `tf.keras.preprocessing.ImageDataGenerator.flow_from_directory`.
                Here you can find all available arguments:
                https://www.tensorflow.org/api_docs/python/tf/keras/preprocessing/image/ImageDataGenerator#flow_from_directory
                All defaults are preserved.
        """
        self.directory = directory
        self.generator_args = generator_args
        self.load_args = load_args
        self.save_args = save_args 

    def _load(self):
        generator = tf.keras.preprocessing.ImageDataGenerator(**self.generator_args)
        return generator.flow_from_directory(self.directory, **self.load_args)

    def _save(self, data):
        raise Exception("Saving with the FlowFromDirectoryDataSet is not supported")
    
    
# TODO FlowDataSet