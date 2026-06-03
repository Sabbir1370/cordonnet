"""Status command."""
import typer
from rich.console import Console
from rich.table import Table
from cordonnet.core.config_manager import ConfigManager
from cordonnet.services.systemd_service import SystemdServiceManager
from cordonnet.core.client_manager import ClientManager
from cordonnet.services.hostapd_service import SERVICE_NAME as HS, VIRTUAL_IFACE
from cordonnet.services.dnsmasq_service import SERVICE_NAME as DS

console = Console()

def show_status():
    """Show hotspot and network status."""
    cfg = ConfigManager().get()
    table = Table(title="CordonNet Status")
    table.add_column("Property", style="bold blue")
    table.add_column("Value", style="cyan")

    sysd = SystemdServiceManager()
    hotspot_running = sysd.is_active(HS)
    dnsmasq_running = sysd.is_active(DS)
    clients = ClientManager(subnet=cfg.subnet).list_clients()

    table.add_row("Hotspot", "Running" if hotspot_running else "Stopped")
    table.add_row("SSID", cfg.ssid)
    table.add_row("Virtual Interface", VIRTUAL_IFACE if hotspot_running else "N/A")
    table.add_row("Base Interface", cfg.interface)
    table.add_row("Access Mode", cfg.security.mode.capitalize())
    table.add_row("Internet", "Enabled" if cfg.internet.enabled else "Disabled")
    table.add_row("Connected Clients", str(len(clients)))
    table.add_row("Gateway", cfg.gateway)
    table.add_row("Client Isolation", "On" if cfg.security.client_isolation else "Off")
    console.print(table)