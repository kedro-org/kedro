# Test a Kedro project

It is important to test our Kedro projects to validate and verify that our nodes and pipelines behave as we expect them to. In this section we look at some example tests for the spaceflights project.

This section explains the following:

* How to test a Kedro node
* How to test a Kedro pipeline
* Testing best practices


This section does not cover:

* Automating your tests - instead refer to our [automated testing documentation](../development/automated_testing.md).
* More advanced features of testing, including [mocking](https://realpython.com/python-mock-library/#what-is-mocking) and [parametrizing tests](https://docs.pytest.org/en/7.1.x/example/parametrize.html).


## Writing tests for Kedro nodes: Unit testing

We define our node functions as [pure functions](https://realpython.com/python-functional-programming/#what-is-functional-programming); a pure function is one whose output value follows solely from its input values, without any observable side effects such as changes to state or mutable data. When testing these functions we check that for a given set of input values, a node will produce the expected output. This type of test is referred to as a unit test. 

Let us explore what this looks like in practice. Consider the node function `split_data` defined in the data science pipeline:

<details>
<summary><b>Click to expand</b></summary>

```python
def split_data(data: pd.DataFrame, parameters: Dict) -> Tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data: Data containing features and target.
        parameters: Parameters defined in parameters_data_science.yml.
    Returns:
        Split data.
    """
    X = data[parameters["features"]]
    y = data["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )
    return X_train, X_test, y_train, y_test
```

</details>

The function takes a pandas DataFrame and dictionary of parameters as input, and splits the input data into 4 different data objects as per the parameters provided. We recommend following [pytest's anatomy of a test](https://docs.pytest.org/en/7.1.x/explanation/anatomy.html#anatomy-of-a-test) which breaks a test down into 4  steps: arrange, act, assert, and cleanup. For this specific function, these steps will be:

1. Arrange: Prepare the inputs `data` and `parameters`.
2. Act: Make a call to `split_data` and capture the outputs with `X_train`, `X_test`, `Y_train`, and `Y_test`.
3. Assert: Ensure that the length of the outputs are the same as the expected lengths

Cleanup is not required for this test. Remember to import the function being tested and any necessary modules at the top of the file. 

When we put these steps together, we have the following test:

<details>
<summary><b>Click to expand</b></summary>

```python
# NOTE: This example test is yet to be refactored. 
# A complete version is available under the testing best practices section.

import pandas as pd
from spaceflights.pipelines.data_science.nodes import split_data

    def test_split_data():
        # Arrange
        dummy_data = pd.DataFrame(
        {"engines": [1, 2, 3],
         "crew": [4, 5, 6],
         "passenger_capacity": [5, 6, 7],
         "price": [120, 290, 30]})

        dummy_parameters = {"model_options":
                     {"test_size": 0.2,
                      "random_state": 3,
                      "features": ["engines", "passenger_capacity", "crew"]}}

        # Act
        X_train, X_test, y_train, y_test = split_data(dummy_data, dummy_parameters["model_options"])

        # Assert
        assert len(X_train) == 2
        assert len(y_train) == 2
        assert len(X_test) == 1
        assert len(y_test) == 1
```

</details>


## Writing tests for Kedro pipelines: Integration testing

Writing tests for each node ensures each node will behave as expected when run individually. However, we must consider how nodes in a pipeline interact with each other - this is called integration testing. Integration testing combines individual units as a group and checks whether they communicate correctly, share data properly, and work as expected when combined. Let us look at this in practice.

Consider the data science pipeline as a whole:

<details>
<summary><b>Click to expand</b></summary>

```python
from kedro.pipeline import Pipeline, node, pipeline
from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
                name="split_data_node",
            ),
            node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
            node(
                func=evaluate_model,
                inputs=["regressor", "X_test", "y_test"],
                outputs=None,
                name="evaluate_model_node",
            ),
        ]
    )
```
</details>

The pipeline takes a DataFrame and dictionary of parameters as input, splits the data in accordance to the parameters, and uses it to train and evaluate a regression model. With an integration test, we can validate that this sequence of nodes runs as expected. As we did with our unit tests, we break this down into several steps:

1. Arrange: Prepare the runner and its inputs `pipeline` and `catalog`.
2. Act: Run the pipeline.
3. Assert: Ensure the outputs are as expected.

When we put this together, we get the following test:

<details>
<summary><b>Click to expand</b></summary>

```python
# NOTE: This example test is yet to be refactored. 
# A complete version is available under the testing best practices section.

import pandas as pd
from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline

    def test_data_science_pipeline():
        # Arrange pipeline
        pipeline = create_pipeline()
        
        # Arrange data catalog 
        catalog = DataCatalog()

        dummy_data = pd.DataFrame(
        {"engines": [1, 2, 3],
         "crew": [4, 5, 6],
         "passenger_capacity": [5, 6, 7],
         "price": [120, 290, 30]})
        catalog.add("model_input_table", MemoryDataset(dummy_data))
        
        dummy_parameters = {"model_options":
                     {"test_size": 0.2,
                      "random_state": 3,
                      "features": ["engines", "passenger_capacity", "crew"]}}
        catalog.add_feed_dict({"params:model_options" : dummy_parameters["model_options"]})

        # Act
        output = SequentialRunner().run(pipeline, catalog)
        
        # Assert
        assert len(output) == 0

```

</details>

## Testing best practices

### Where to write your tests

We recommend creating a `tests` directory within the root directory of your project. The structure should mirror the directory structure of `/src/spaceflights`:

```
src
│   ...
└───spaceflights
│   └───pipelines
│       └───data_science
│           │   __init__.py
│           │   nodes.py
│           │   pipeline.py
│
tests
|   ...
└───pipelines
    |    test_data_science_pipeline.py
```

Within `test_data_science.py` you can use [test classes](https://docs.pytest.org/en/7.1.x/getting-started.html#group-multiple-tests-in-a-class) to further organise your tests.

### Using fixtures

In our tests, we can see that `dummy_data` and `dummy_parameters` have been defined twice with the same values. Instead, we can define these outside of our tests as [pytest fixtures](https://docs.pytest.org/en/6.2.x/fixture.html#fixture):

<details>

```python
import pytest

@pytest.fixture
def dummy_data():
    return pd.DataFrame(
        {"engines": [1, 2, 3],
         "crew": [4, 5, 6],
         "passenger_capacity": [5, 6, 7],
         "price": [120, 290, 30]})

@pytest.fixture
def dummy_parameters():
    parameters = {"model_options":
                     {"test_size": 0.2,
                      "random_state": 3,
                      "features": ["engines", "passenger_capacity", "crew"]}
                 }
    return parameters
```

</details>

We can then access these through the test arguments.

```python
def test_split_data(self, dummy_data, dummy_parameters):
        ...
```

### Pipeline slicing

In the test `test_data_science_pipeline` we test the that outputs of the data science pipeline are those that are expected. However, as pipelines are not static, this test is not robust. Instead we should be specific with how we define the pipeline to be tested; we do this by using [pipeline slicing](../nodes_and_pipelines/slice_a_pipeline.md#slice-a-pipeline-by-running-specified-nodes) to specify the pipeline's start and end:

```python
    def test_data_science_pipeline(self):
        # Arrange pipeline
        pipeline = create_pipeline().from_nodes("split_data_node").to_nodes("evaluate_model_node")
        ...
```

This ensures that the test will still perform as designed, even with the addition of more nodes to the pipeline.


After incorporating these testing practices, our test file `test_data_science.py` becomes:

<details>

```python
# tests/pipelines/test_data_science_pipeline.py

import pandas as pd
import pytest

from kedro.io import DataCatalog, MemoryDataset
from kedro.runner import SequentialRunner
from spaceflights.pipelines.data_science import create_pipeline
from spaceflights.pipelines.data_science.nodes import split_data

@pytest.fixture
def dummy_data():
    return pd.DataFrame(
        {"engines": [1, 2, 3],
         "crew": [4, 5, 6],
         "passenger_capacity": [5, 6, 7],
         "price": [120, 290, 30]})

@pytest.fixture
def dummy_parameters():
    parameters = {"model_options":
                     {"test_size": 0.2,
                      "random_state": 3,
                      "features": ["engines", "passenger_capacity", "crew"]}
                 }
    return parameters


class TestDataScienceNodes:
    def test_split_data(self, dummy_data, dummy_parameters):
        X_train, X_test, y_train, y_test = split_data(dummy_data, dummy_parameters["model_options"])
        assert len(X_train) == 2
        assert len(y_train) == 2
        assert len(X_test) == 1
        assert len(y_test) == 1

class TestDataSciencePipeline:
    def test_data_science_pipeline(self, dummy_data, dummy_parameters):
        pipeline = create_pipeline().from_nodes("split_data_node").to_nodes("evaluate_model_node")
        catalog = DataCatalog()
        catalog.add("model_input_table", MemoryDataset(dummy_data))
        catalog.add_feed_dict({"params:model_options" : dummy_parameters["model_options"]})

        output = SequentialRunner().run(pipeline, catalog)
        assert len(output) == 0

```

</details>

## Run your tests

Ensure you have `pytest` installed. Please see our [automated testing documentation](../development/automated_testing.md) for more information on getting set up with pytest.

To run your tests, run `pytest` from within your project's root directory.

```bash
cd <project_root>
pytest tests/pipelines/test_data_science.py
```

You should see the following output in your shell.

```
============================= test session starts ==============================
...
collected 2 items

tests/pipelines/test_data_science.py ..                                                  [100%]

============================== 2 passed in 4.38s ===============================
```

This output indicates that both tests ran successfully in the file `tests/pipelines/test_data_science.py`.