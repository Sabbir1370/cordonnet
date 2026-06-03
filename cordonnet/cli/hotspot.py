"""CLI commands for hotspot management."""
import typer
from rich.console import Console
from rich.table import Table
from cordonnet.core.config_manager import ConfigManager
from cordonnet.core.hotspot_manager import HotspotManager
from cordonnet.utils.validation import validate_ssid, validate_wifi_password
from cordonnet.models.config import MacEntry

app = typer.Typer(help="Manage the virtual AP hotspot — start, stop, configure SSID/password, and control MAC access lists.")
console = Console()

def get_manager():
    cfg = ConfigManager().get()
    return HotspotManager(cfg)

@app.command()
def start(isolated: bool = typer.Option(False, "--isolated", help="Start hotspot without internet sharing")):
    """Start virtual AP hotspot (single-interface, no Wi‑Fi drop)."""
    try:
        mgr = get_manager()
        mgr.start(isolated=isolated)
        console.print("[green]Virtual hotspot started.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def stop():
    """Stop the hotspot and restore normal Wi‑Fi."""
    try:
        mgr = get_manager()
        mgr.stop()
        console.print("[yellow]Hotspot stopped, Wi‑Fi restored.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def restart(isolated: bool = typer.Option(False, "--isolated")):
    """Restart the hotspot."""
    try:
        mgr = get_manager()
        mgr.restart(isolated=isolated)
        console.print("[green]Hotspot restarted.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def set_ssid(ssid: str):
    """Change the SSID (1-32 chars)."""
    if not validate_ssid(ssid):
        console.print("[red]Invalid SSID.[/red]")
        raise typer.Exit(1)
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    cfg.ssid = ssid
    cfg_mgr.save()
    console.print(f"[green]SSID set to '{ssid}'.[/green]")

@app.command()
def set_password(password: str):
    """Change the WiFi password (8-63 ASCII chars)."""
    if not validate_wifi_password(password):
        console.print("[red]Invalid password.[/red]")
        raise typer.Exit(1)
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    cfg.password = password
    cfg_mgr.save()
    console.print("[green]Password updated.[/green]")

@app.command()
def mode(mode: str = typer.Argument(..., help="Access mode: 'normal' or 'whitelist'")):
    """Switch between 'normal' (blacklist only) and 'whitelist' (only whitelisted MACs allowed)."""
    if mode not in ("normal", "whitelist"):
        console.print("[red]Mode must be 'normal' or 'whitelist'.[/red]")
        raise typer.Exit(1)
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    cfg.security.mode = mode
    cfg_mgr.save()
    console.print(f"[green]Access mode set to '{mode}'.[/green]")


@app.command()
def set_interface(interface: str):
    """Change the base Wi-Fi interface (e.g. wlp1s0, wlan0)."""
    from cordonnet.utils.validation import validate_interface_name
    if not validate_interface_name(interface):
        console.print("[red]Invalid interface name.[/red]")
        raise typer.Exit(1)
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    cfg_mgr.config = cfg.model_copy(update={"interface": interface})
    cfg_mgr.save()
    console.print(f"[green]Interface set to '{interface}'.[/green]")

# Whitelist commands
@app.command()
def whitelist_add(mac: str, name: str = typer.Option("", "--name", help="Optional device/user name")):
    """Add a MAC address to the whitelist."""
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    entry = MacEntry(mac=mac, name=name)
    # Check if already exists
    if any(e.mac == entry.mac for e in cfg.security.whitelist):
        console.print("[yellow]MAC already in whitelist.[/yellow]")
        return
    cfg.security.whitelist.append(entry)
    cfg_mgr.save()
    console.print(f"[green]Added to whitelist: {entry.mac} ({entry.name or 'no name'})[/green]")

@app.command()
def whitelist_remove(mac: str):
    """Remove a MAC address from the whitelist."""
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    before = len(cfg.security.whitelist)
    cfg.security.whitelist = [e for e in cfg.security.whitelist if e.mac != mac.lower()]
    if len(cfg.security.whitelist) == before:
        console.print("[yellow]MAC not found in whitelist.[/yellow]")
        return
    cfg_mgr.save()
    console.print(f"[green]Removed from whitelist: {mac}[/green]")

@app.command("whitelist-list")
def whitelist_list():
    """Show the whitelist."""
    cfg = ConfigManager().get()
    if not cfg.security.whitelist:
        console.print("[dim]Whitelist is empty.[/dim]")
        return
    table = Table(title="Whitelist")
    table.add_column("MAC", style="cyan")
    table.add_column("Name", style="green")
    for entry in cfg.security.whitelist:
        table.add_row(entry.mac, entry.name)
    console.print(table)

# Blacklist commands
@app.command()
def blacklist_add(mac: str, name: str = typer.Option("", "--name", help="Optional device/user name")):
    """Add a MAC address to the blacklist."""
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    entry = MacEntry(mac=mac, name=name)
    if any(e.mac == entry.mac for e in cfg.security.blacklist):
        console.print("[yellow]MAC already in blacklist.[/yellow]")
        return
    cfg.security.blacklist.append(entry)
    cfg_mgr.save()
    console.print(f"[green]Added to blacklist: {entry.mac} ({entry.name or 'no name'})[/green]")

@app.command()
def blacklist_remove(mac: str):
    """Remove a MAC address from the blacklist."""
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    before = len(cfg.security.blacklist)
    cfg.security.blacklist = [e for e in cfg.security.blacklist if e.mac != mac.lower()]
    if len(cfg.security.blacklist) == before:
        console.print("[yellow]MAC not found in blacklist.[/yellow]")
        return
    cfg_mgr.save()
    console.print(f"[green]Removed from blacklist: {mac}[/green]")

@app.command("blacklist-list")
def blacklist_list():
    """Show the blacklist."""
    cfg = ConfigManager().get()
    if not cfg.security.blacklist:
        console.print("[dim]Blacklist is empty.[/dim]")
        return
    table = Table(title="Blacklist")
    table.add_column("MAC", style="cyan")
    table.add_column("Name", style="green")
    for entry in cfg.security.blacklist:
        table.add_row(entry.mac, entry.name)
    console.print(table)