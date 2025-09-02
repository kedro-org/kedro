# Data Science pipeline

> *Note:* This `README.md` was generated using `Kedro {{ cookiecutter.kedro_version }}` for illustration purposes. Please modify it according to your pipeline structure and contents.

## Overview

This modular pipeline:
1. trains a simple multi-class logistic regression model (`train_model` node)
2. makes predictions given a trained model from (1) and a test set (`predict` node)
3. reports the model accuracy on a test set (`report_accuracy` node)


## Pipeline inputs

### `example_train_x`

|      |                    |
| ---- | ------------------ |
| Type | `pandas.DataFrame` |
| Description | DataFrame containing train set features |

### `example_train_y`

|      |                    |
| ---- | ------------------ |
| Type | `pandas.DataFrame` |
| Description | DataFrame containing train set one-hot encoded target variable |

### `example_test_x`

|      |                    |
| ---- | ------------------ |
| Type | `pandas.DataFrame` |
| Description | DataFrame containing test set features |

### `example_test_y`

|      |                    |
| ---- | ------------------ |
| Type | `pandas.DataFrame` |
| Description | DataFrame containing test set one-hot encoded target variable |

### `parameters`

|      |                    |
| ---- | ------------------ |
| Type | `dict` |
| Description | Project parameter dictionary that must contain the following keys: `example_num_train_iter` (number of model training iterations), `example_learning_rate` (learning rate for gradient descent) |


## Pipeline outputs

### `example_model`

|      |                    |
| ---- | ------------------ |
| Type | `numpy.ndarray` |
| Description | Example logistic regression model |
