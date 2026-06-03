"""Input validation functions for CordonNet."""
import re
import ipaddress
from typing import Optional
from pydantic import ValidationError

def validate_interface_name(name: str) -> bool:
    """Check if name is a valid Linux network interface name (simple pattern)."""
    return bool(re.match(r'^[a-zA-Z0-9_\-]+$', name)) and len(name) <= 15

def validate_ssid(ssid: str) -> bool:
    """SSID must be 1-32 characters, valid UTF-8."""
    try:
        ssid.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return 1 <= len(ssid) <= 32

def validate_wifi_password(password: str) -> bool:
    """WPA2 passphrase: 8-63 ASCII characters."""
    if not 8 <= len(password) <= 63:
        return False
    return all(32 <= ord(c) <= 126 for c in password)

def validate_subnet(cidr: str) -> bool:
    """Check if cidr is a valid IPv4 network."""
    try:
        ipaddress.IPv4Network(cidr)
        return True
    except (ValueError, ipaddress.AddressValueError):
        return False

def validate_ip_address(ip: str) -> bool:
    """Check if ip is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False