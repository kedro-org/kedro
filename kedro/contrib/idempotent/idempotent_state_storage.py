import os
from datetime import datetime
from typing import List


class IdempotentStateStorage:

    def __init__(self):
        self.state = {
            # Keyed by node names, values are the current node's key
            # and the input node keys.
            # {
            #   "key": "asdf",
            #   "inputs": {
            #       "node1": "qwerty",
            #       "node2": "zxcv"
            #   }
            # }
        }

    @staticmethod
    def generate_key():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

    def update_key(self, node: str, inputs: List[str]):
        self.state[node]['key'] = IdempotentStateStorage.generate_key()
        self.state[node]['inputs'] = dict([
            self.state.get(target_input, {}).get('key')
            for target_input in inputs
        ])

    def node_inputs_have_changed(self, node, inputs: List[str]):
        expect_inputs = self.state[node]['inputs'].items()
        if sorted(expect_inputs) != sorted(inputs):
            return True

        expect_input_keys = [
            self.state[node]['inputs'].get(input_node)
            for input_node in expect_inputs
        ]

        actual_input_keys = [
            self.state[input_node].get('key')
            for input_node in expect_inputs
        ]

        input_keys = zip(expect_input_keys, actual_input_keys)
        input_keys_not_matching = [
            left != right
            for left, right in input_keys
        ]
        return any(input_keys_not_matching)
