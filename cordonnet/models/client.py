"""Client dataclass used for discovered devices."""
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Client:
    ip: str
    mac: str
    hostname: str = ""
    first_seen: datetime = None