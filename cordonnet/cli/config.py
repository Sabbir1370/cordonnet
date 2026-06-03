"""Configuration viewing/validation."""
import typer
from rich.console import Console
from rich.syntax import Syntax
import yaml
from cordonnet.core.config_manager import ConfigManager

app = typer.Typer(help="View and validate the CordonNet configuration file.")
console = Console()

@app.command("show")
def show():
    """Display current configuration as YAML."""
    cfg_mgr = ConfigManager()
    cfg = cfg_mgr.get()
    yaml_str = yaml.dump(cfg.model_dump(), default_flow_style=False)
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
    console.print(syntax)

@app.command("validate")
def validate():
    """Validate the configuration file for errors."""
    try:
        ConfigManager()
        console.print("[green]Configuration is valid.[/green]")
    except Exception as e:
        console.print(f"[red]Invalid configuration: {e}[/red]")
        raise typer.Exit(code=1)