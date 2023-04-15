import dataclasses

from models.client import Client


@dataclasses.dataclass
class Subscription:
    client: Client
    topic: str
    qos: int
