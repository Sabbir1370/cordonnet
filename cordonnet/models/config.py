from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict
import ipaddress
import re

class MacEntry(BaseModel):
    mac: str
    name: str = ""

    @field_validator('mac')
    @classmethod
    def validate_mac(cls, v: str) -> str:
        if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', v):
            raise ValueError('Invalid MAC address format (xx:xx:xx:xx:xx:xx)')
        return v.lower()

class DHCPConfig(BaseModel):
    start: str = "192.168.50.10"
    end: str = "192.168.50.100"

    @field_validator('start', 'end')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        ipaddress.IPv4Address(v)
        return v

class InternetConfig(BaseModel):
    enabled: bool = False

class SecurityConfig(BaseModel):
    client_isolation: bool = True
    mode: str = "normal"   # "normal" or "whitelist"
    whitelist: List[MacEntry] = Field(default_factory=list)
    blacklist: List[MacEntry] = Field(default_factory=list)

    @field_validator('mode')
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("normal", "whitelist"):
            raise ValueError('Mode must be "normal" or "whitelist"')
        return v

class LabConfig(BaseModel):
    auto_start_ctf: bool = False
    backend_port: int = Field(8000, ge=1, le=65535)

class AppConfig(BaseModel):
    ssid: str = "CordonCTF"
    password: str = "changeme123"
    interface: str = "wlp1s0"          # physical Wi-Fi interface (base)
    subnet: str = "192.168.50.0/24"
    gateway: str = "192.168.50.1"
    dhcp: DHCPConfig = DHCPConfig()
    internet: InternetConfig = InternetConfig()
    security: SecurityConfig = SecurityConfig()
    lab: LabConfig = LabConfig()

    @field_validator('ssid')
    @classmethod
    def ssid_length(cls, v: str) -> str:
        if not (1 <= len(v) <= 32):
            raise ValueError('SSID must be 1-32 characters')
        return v

    @field_validator('password')
    @classmethod
    def wifi_password_strength(cls, v: str) -> str:
        if not (8 <= len(v) <= 63):
            raise ValueError('Password must be 8-63 characters')
        if not all(32 <= ord(c) <= 126 for c in v):
            raise ValueError('Password must be printable ASCII')
        return v

    @field_validator('subnet')
    @classmethod
    def valid_subnet(cls, v: str) -> str:
        ipaddress.IPv4Network(v)
        return v

    @field_validator('gateway')
    @classmethod
    def valid_gateway(cls, v: str) -> str:
        ipaddress.IPv4Address(v)
        return v