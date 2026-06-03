"""Rich-renderable status model."""
from dataclasses import dataclass
from typing import Optional
from cordonnet.models.client import Client
from datetime import datetime

@dataclass
class HotspotStatus:
    is_running: bool
    ssid: str = ""
    interface: str = ""
    internet_enabled: bool = False
    connected_clients: int = 0
    gateway: str = ""