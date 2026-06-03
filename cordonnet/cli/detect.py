"""Detect if virtual AP is supported."""
import typer
from rich.console import Console
from cordonnet.utils.detection import get_phy_capabilities

console = Console()

def detect():
    """Check if your Wi-Fi hardware supports virtual AP mode."""
    phys = get_phy_capabilities()
    if any(p.supports_ap for p in phys):
        console.print("[green]✓ Virtual AP mode is supported on this hardware.[/green]")
    else:
        console.print("[red]✗ AP mode not supported. Virtual AP cannot be created.[/red]")