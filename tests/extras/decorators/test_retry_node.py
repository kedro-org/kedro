import pytest

from kedro.extras.decorators.retry_node import retry
from kedro.pipeline import node


def test_retry():
    def _bigger(obj):
        obj["value"] += 1
        if obj["value"] >= 0:
            return True
        raise ValueError("Value less than 0")

    decorated = node(_bigger, "in", "out").decorate(retry())

    with pytest.raises(ValueError, match=r"Value less than 0"):
        decorated.run({"in": {"value": -3}})

    decorated2 = node(_bigger, "in", "out").decorate(retry(n_times=2))
    assert decorated2.run({"in": {"value": -3}})
