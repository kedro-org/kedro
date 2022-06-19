import pytest
from requests.auth import HTTPBasicAuth

from kedro.extras.datasets.api.auth_factory import create_authenticator
from kedro.io import DataSetError


class TestAuthFactory:
    def test_http_basic_auth(self):
        authenticator = create_authenticator(
            "requests.auth.HTTPBasicAuth", username="John", password="Doe"
        )
        assert isinstance(authenticator, HTTPBasicAuth)

    def test_class_path_not_found(self):
        with pytest.raises(DataSetError, match="cannot be found"):
            create_authenticator("unfindable.class")

    def test_class_wrong_arguments(self):
        with pytest.raises(DataSetError, match="valid for the constructor of"):
            create_authenticator("requests.auth.HTTPBasicAuth", pan="cake")

    def test_class_cannot_instantiate(self):
        with pytest.raises(DataSetError, match="Failed to instantiate"):
            create_authenticator(
                "kedro.pipeline.node.Node",
                func="func",
                inputs="input_node",
                outputs="output_node",
            )

    def test_class_not_of_type_auth_base(self):
        with pytest.raises(DataSetError, match="instance of AuthBase"):
            create_authenticator(
                "kedro.pipeline.node.Node",
                func=lambda: True,
                inputs=None,
                outputs="output_node",
            )
