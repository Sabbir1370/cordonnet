"""Client discovery and tracking."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import re
import logging
from ipaddress import IPv4Network, IPv4Address, AddressValueError

from cordonnet.models.client import Client
from cordonnet.utils.shell import run_checked

logger = logging.getLogger("cordonnet.clients")

DEFAULT_LEASE_FILE = Path("/run/cordonnet/dnsmasq.leases")

class ClientManager:
    def __init__(self, lease_file: Path = DEFAULT_LEASE_FILE, subnet: str = None):
        self.lease_file = lease_file
        self.subnet = IPv4Network(subnet) if subnet else None

    def _parse_leases(self) -> List[Client]:
        clients = []
        if not self.lease_file.exists():
            logger.warning("Lease file %s not found.", self.lease_file)
            return clients

        for line in self.lease_file.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) >= 3:
                timestamp = int(parts[0])
                mac = parts[1]
                ip = parts[2]
                hostname = parts[3] if len(parts) > 3 else ""
                clients.append(Client(
                    ip=ip,
                    mac=mac,
                    hostname=hostname,
                    first_seen=datetime.fromtimestamp(timestamp)
                ))
        return clients

    def _parse_ip_neigh(self) -> List[Client]:
        """Extract clients from `ip neigh` – only IPv4 entries."""
        clients = []
        try:
            out = run_checked(["ip", "neigh", "show"])
            for line in out.splitlines():
                # Format: <ip> dev <dev> lladdr <mac> STALE/REACHABLE
                match = re.match(r'(\S+)\s+dev\s+\S+\s+lladdr\s+(\S+)', line)
                if match:
                    ip_str = match.group(1)
                    mac = match.group(2)
                    # Skip non-IPv4 (e.g., IPv6)
                    try:
                        IPv4Address(ip_str)
                    except AddressValueError:
                        continue
                    if not any(c.ip == ip_str for c in clients):
                        clients.append(Client(ip=ip_str, mac=mac))
        except Exception as e:
            logger.warning("Could not read ARP table: %s", e)
        return clients

    def list_clients(self) -> List[Client]:
        leases = self._parse_leases()
        arp_clients = self._parse_ip_neigh()
        merged = leases.copy()
        lease_ips = {c.ip for c in leases}
        for c in arp_clients:
            if c.ip not in lease_ips:
                merged.append(c)
        # Filter to the configured subnet (if any)
        if self.subnet:
            valid = []
            for c in merged:
                try:
                    if IPv4Address(c.ip) in self.subnet:
                        valid.append(c)
                except AddressValueError:
                    pass
            merged = valid
        return merged

    def lookup(self, identifier: str) -> Optional[Client]:
        for c in self.list_clients():
            if c.ip == identifier or c.mac.lower() == identifier.lower():
                return c
        return None