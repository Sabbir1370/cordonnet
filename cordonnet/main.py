"""CordonNet CLI entry point."""
import typer
from cordonnet.cli import hotspot, clients, config
from cordonnet.cli.status import show_status
from cordonnet.cli.detect import detect
from cordonnet.utils.logging import setup_logging

setup_logging()

app = typer.Typer(
    name="cordonnet",
    help="Single-interface virtual AP manager. Creates a virtual Wi-Fi hotspot on your existing Wi-Fi card without dropping your internet connection.",
    no_args_is_help=True,
)

@app.callback()
def callback():
    pass

app.add_typer(hotspot.app,  name="hotspot")
app.add_typer(clients.app,  name="clients")
app.add_typer(config.app,   name="config")
app.command(name="status")(show_status)
app.command(name="detect")(detect)

if __name__ == "__main__":
    app()