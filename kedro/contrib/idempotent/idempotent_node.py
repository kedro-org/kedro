from typing import Dict, Any
from uuid import uuid4

from kedro.config import ConfigLoader
from kedro.pipeline.node import Node


class IdempotentNode(Node):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.idempotent_config = ConfigLoader(['conf/base', 'conf/local']).get('idempotent*')

    def run(self, inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        ret = super().run(inputs)
        return ret

    @staticmethod
    def generate_idempotency_id():
        return str(uuid4())
