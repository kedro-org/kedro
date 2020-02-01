import os
from uuid import uuid4
from typing import List

from kedro.io import JSONLocalDataSet
from kedro.io.core import DataSetError

NODE_STATE_FILE_PATH = os.getcwd() + '/data/01_raw/node_state.json'


class IdempotentStateStorage:

    def __init__(self, state=None):
        self.state = state if state else self._load_state()

    def _load_state(self):
        try:
            initial_state = JSONLocalDataSet(filepath=NODE_STATE_FILE_PATH).load()
        except DataSetError:
            initial_state = {
                # Keyed by node names, values are the current node's key
                # and the input node keys.
                # {
                #   "key": "asdf-asdf-sadf",
                #   "inputs": {
                #       "node1": "qwer-qwer-qwer",
                #       "node2": "zxcv-zxcv-zxcv"
                #   }
                # }
            }
        return initial_state

    def save_state(self):
        JSONLocalDataSet(filepath=NODE_STATE_FILE_PATH).save(self.state)

    @staticmethod
    def generate_key():
        return str(uuid4())

    def update_key(self, node: str, inputs: List[str]):
        self.state[node]['key'] = IdempotentStateStorage.generate_key()
        self.state[node]['inputs'] = {
            target_input: self.state.get(target_input, {}).get('key')
            for target_input in inputs
        }
        return self.state

    def node_inputs_have_changed(self, node, inputs: List[str]):
        expect_input_items = self.state[node]['inputs'].items()

        # If any inputs are new or removed, node should be run
        expect_inputs = [input_node for input_node, key in expect_input_items]
        if sorted(expect_inputs) != sorted(inputs):
            return True

        expect_input_keys = [
            key
            for input_node, key in expect_input_items
        ]

        actual_input_keys = [
            self.state[input_node].get('key')
            for input_node, key in expect_input_items
        ]

        input_keys = zip(expect_input_keys, actual_input_keys)
        input_keys_not_matching = [
            left != right
            for left, right in set(input_keys)
        ]

        return any(input_keys_not_matching)
