"""Generate dnsmasq configuration and manage via systemd."""
from pathlib import Path
import logging
from cordonnet.models.config import AppConfig
from cordonnet.services.systemd_service import SystemdServiceManager
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("cordonnet.hotspot")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
CONF_FILE = Path("/run/cordonnet/dnsmasq.conf")
LEASE_FILE = Path("/run/cordonnet/dnsmasq.leases")
SERVICE_NAME = "cordonnet-dnsmasq"

class DnsmasqService:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        self.systemd = SystemdServiceManager()

    def generate_config(self, config: AppConfig) -> str:
        template = self.env.get_template("dnsmasq.conf.j2")
        return template.render(
            interface="cord-ap0",
            dhcp=config.dhcp,
            gateway=config.gateway,
            internet=config.internet,
            security=config.security
        )

    def start(self, config: AppConfig) -> None:
        content = self.generate_config(config)
        CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONF_FILE.write_text(content)
        LEASE_FILE.touch()

        self.systemd.create_service(
            unit_name=SERVICE_NAME,
            exec_start=f"/usr/sbin/dnsmasq -k -C {CONF_FILE} -l {LEASE_FILE}",
            description="CordonNet DHCP/DNS server"
        )
        self.systemd.start_service(SERVICE_NAME)

    def stop(self) -> None:
        self.systemd.stop_service(SERVICE_NAME)
        # Clean up both config and lease files
        for f in (CONF_FILE, LEASE_FILE):
            if f.exists():
                f.unlink()
                logger.debug("Removed %s", f)