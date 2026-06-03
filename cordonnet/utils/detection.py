"""Hardware and capability detection using iw and ip."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import logging
from cordonnet.utils.shell import run_checked

logger = logging.getLogger("cordonnet.app")

@dataclass
class WirelessInterface:
    name: str
    mac: str
    current_mode: str
    phy: str = ""

@dataclass
class PhyCapabilities:
    phy_name: str
    supports_ap: bool = False
    supports_monitor: bool = False
    interface_combinations: List[Dict[str, Any]] = field(default_factory=list)
    band_5ghz: bool = False
    band_2ghz: bool = False

def get_wireless_interfaces() -> List[WirelessInterface]:
    try:
        out = run_checked(["iw", "dev"])
    except Exception as e:
        logger.error("Failed to run iw dev: %s", e)
        return []

    interfaces = []
    current_name = None
    current_mac = None
    current_type = None

    for line in out.splitlines():
        stripped = line.strip()
        if stripped.startswith("Interface "):
            if current_name and current_mac and current_type:
                interfaces.append(WirelessInterface(name=current_name, mac=current_mac, current_mode=current_type))
            current_name = stripped.split()[1]
            current_mac = None
            current_type = None
        elif stripped.startswith("addr "):
            current_mac = stripped.split()[1]
        elif stripped.startswith("type "):
            current_type = stripped.split()[1]

    if current_name and current_mac and current_type:
        interfaces.append(WirelessInterface(name=current_name, mac=current_mac, current_mode=current_type))

    # Enrich with phy info
    for iface in interfaces:
        try:
            info = run_checked(["iw", "dev", iface.name, "info"])
            for iline in info.splitlines():
                if iline.strip().startswith("wiphy "):
                    iface.phy = iline.strip().split()[1]
                    break
        except Exception:
            pass

    return interfaces

def get_phy_capabilities() -> List[PhyCapabilities]:
    try:
        out = run_checked(["iw", "list"])
    except Exception as e:
        logger.error("Failed to run iw list: %s", e)
        return []

    phys = []
    current_phy = None
    for line in out.splitlines():
        stripped = line.strip()
        if stripped.startswith("Wiphy "):
            if current_phy:
                phys.append(current_phy)
            current_phy = PhyCapabilities(phy_name=stripped.split()[1])
        elif current_phy:
            if stripped.startswith("* AP"):
                current_phy.supports_ap = True
            if stripped.startswith("* monitor"):
                current_phy.supports_monitor = True
            if "5180.0 MHz" in stripped:
                current_phy.band_5ghz = True
            if "2412.0 MHz" in stripped:
                current_phy.band_2ghz = True

    if current_phy:
        phys.append(current_phy)
    return phys

def can_ap_mode(interface_name: str) -> bool:
    phys = get_phy_capabilities()
    return any(phy.supports_ap for phy in phys) if phys else False