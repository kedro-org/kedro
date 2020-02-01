import os
from datetime import datetime
from typing import List


class IdempotentStateStorage:

    def __init__(self, state=None):
        self.state = state if state else {
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
