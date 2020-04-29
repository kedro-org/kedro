# Transformer #

## Time profiler ##
By importing **```AbstractTransformer```**, the class **```ProfileTimeTransformer```** enables the users to record & log the dataset load and save calls for the respective dataset.

**Methods & Examples:**

| Command | Description |
| --- | --- |
| **```ProfileTimeTransformer.load```**(data_set_name, load) | Wrapping the loading of the dataset. |
| **```ProfileTimeTransformer.save```**(data_set_name, ...) | Wrapping the saving of the dataset. |

> **```load```**(data_setname,load)

This is for wrapping the loading of a dataset. Call **```load```** to retreive the data from the given dataset/next transformer.

**Parameters:**
  - data_set_name(**```str```**) - The name of the dataset that is being loaded.
  - load(**```callable```**[[],**```Any```**]) - A callback to retreive the data that is being loaded from the given dataset/next transformer.

**Return Type:** **```Any```**

**Returns:** The loaded data.


> **```save```**(data_setname,save,data)

This is for wrapping the save of a dataset. Call**```Save```** to pass the data to the dataset/next transformer.

**Parameters:**
  - data_set_name(**```str```**) - The name of the dataset that is being saved.
  - load(**```callable```**[[**```Any```**],**```None```**]) - A callback to pass the data that is being saved onto the given dataset/next transformer.
  - data(**```Any```**) - The data which have been saved.

**Return Type:** **```None```**
