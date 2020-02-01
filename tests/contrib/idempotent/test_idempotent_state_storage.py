import pytest
import random

from kedro.contrib.idempotent.idempotent_state_storage import IdempotentStateStorage


@pytest.fixture
def state_storage_no_update():
    # Pipeline: node3 -> node2 -> node1
    nodes = ['node1', 'node2', 'node3']
    keys = [1, 2, 3]
    return {
        node: {
            "key": keys[node_index],
            "inputs": {
                nodes[input_node_index]: keys[input_node_index]
                for input_node_index in range(node_index)
            }
        }
        for node_index, node in enumerate(nodes)
    }


@pytest.fixture
def state_storage_with_update():
    # Pipeline: node3 -> node2 -> node1
    nodes = ['node1', 'node2', 'node3']
    keys = [1, 2, 3]
    return {
        node: {
            "key": random.choice(range(10, 20)),
            "inputs": {
                nodes[input_node_index]: keys[input_node_index]
                for input_node_index in range(node_index)
            }
        }
        for node_index, node in enumerate(nodes)
    }


class TestIdempotentStateStorage:

    def test_node_inputs_have_not_changed(self, state_storage_no_update):
        storage = IdempotentStateStorage(state_storage_no_update)
        assert not storage.node_inputs_have_changed('node3', ['node2', 'node1'])

    def test_node_inputs_have_changed(self, state_storage_with_update):
        storage = IdempotentStateStorage(state_storage_with_update)
        assert storage.node_inputs_have_changed('node3', ['node2', 'node1'])
        assert storage.node_inputs_have_changed('node3', ['node2'])

    def test_update_dey(self, state_storage_with_update):
        storage = IdempotentStateStorage(state_storage_with_update)
        updated_state = storage.update_key('node3', ['node2', 'node1'])

        assert updated_state['node3']['inputs']['node2'] == updated_state['node2']['key']
        assert updated_state['node3']['inputs']['node1'] == updated_state['node1']['key']

        updated_state = storage.update_key('node3', ['node2'])
        assert updated_state['node3']['inputs']['node2'] == updated_state['node2']['key']
        assert not updated_state['node3']['inputs'].get('node1', None)
