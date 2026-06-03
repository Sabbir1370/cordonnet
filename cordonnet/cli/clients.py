"""CLI for client listing."""
import typer
from rich.console import Console
from rich.table import Table
from cordonnet.core.client_manager import ClientManager
from cordonnet.core.config_manager import ConfigManager

app = typer.Typer(help="Monitor devices connected to the hotspot — list all clients or look one up by IP or MAC.")
console = Console()

@app.command("list")
def list_clients():
    """List connected clients."""
    cfg = ConfigManager().get()
    mgr = ClientManager(subnet=cfg.subnet)
    clients = mgr.list_clients()
    if not clients:
        console.print("[yellow]No clients connected.[/yellow]")
        return
    table = Table(title="Connected Clients")
    table.add_column("IP", style="cyan")
    table.add_column("MAC", style="magenta")
    table.add_column("Hostname", style="green")
    table.add_column("First Seen", style="blue")
    for c in clients:
        table.add_row(c.ip, c.mac, c.hostname, str(c.first_seen) if c.first_seen else "-")
    console.print(table)

@app.command()
def lookup(identifier: str):
    """Lookup a client by IP or MAC."""
    cfg = ConfigManager().get()
    mgr = ClientManager(subnet=cfg.subnet)
    client = mgr.lookup(identifier)
    if client:
        console.print(client)
    else:
        console.print("[red]Client not found.[/red]")