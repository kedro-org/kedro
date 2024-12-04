from kedro.pipeline import Pipeline, node
from .nodes import create_data, process_data

def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(func=create_data, inputs=None, outputs="raw_data", name="create_data_node"),
            node(func=process_data, inputs="raw_data", outputs="processed_data", name="process_data_node"),
        ]
    )