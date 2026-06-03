"""Generate hostapd config and manage virtual AP."""
from pathlib import Path
import logging
import re
from cordonnet.models.config import AppConfig
from cordonnet.services.systemd_service import SystemdServiceManager
from cordonnet.utils.shell import run_sudo_checked, run_checked
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger("cordonnet.hotspot")

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
CONF_FILE = Path("/run/cordonnet/hostapd.conf")
SERVICE_NAME = "cordonnet-hotspot"
VIRTUAL_IFACE = "cord-ap0"

class HostapdService:
    def __init__(self):
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
        self.systemd = SystemdServiceManager()
        self.virtual_iface = VIRTUAL_IFACE

    def _get_current_channel(self, physical_iface: str) -> str:
        try:
            out = run_sudo_checked(["iw", "dev", physical_iface, "info"])
            match = re.search(r'channel\s+(\d+)', out)
            if match:
                channel = match.group(1)
                logger.info("Detected channel %s on %s.", channel, physical_iface)
                return channel
        except Exception as e:
            logger.warning("Could not detect channel on %s: %s. Defaulting to 6.", physical_iface, e)
        return "6"

    def _iface_exists(self) -> bool:
        try:
            run_checked(["ip", "link", "show", self.virtual_iface])
            return True
        except Exception:
            return False

    def _remove_virtual_iface(self) -> None:
        if not self._iface_exists():
            return
        try:
            run_sudo_checked(["iw", "dev", self.virtual_iface, "del"])
            logger.debug("Removed %s via iw.", self.virtual_iface)
            return
        except Exception as e:
            logger.debug("iw del failed (%s), trying ip link del.", e)
        try:
            run_sudo_checked(["ip", "link", "del", self.virtual_iface])
            logger.debug("Removed %s via ip link del.", self.virtual_iface)
        except Exception as e:
            logger.warning("Could not remove %s: %s", self.virtual_iface, e)

    def _set_nm_unmanaged(self, iface: str) -> None:
        """Tell NetworkManager to leave an interface alone."""
        try:
            run_sudo_checked(["nmcli", "device", "set", iface, "managed", "no"])
            logger.debug("NM: set %s unmanaged.", iface)
        except Exception as e:
            logger.debug("nmcli not available or failed (%s), ignoring.", e)

    def _set_nm_managed(self, iface: str) -> None:
        """Return an interface to NetworkManager control."""
        try:
            run_sudo_checked(["nmcli", "device", "set", iface, "managed", "yes"])
            logger.debug("NM: set %s managed.", iface)
        except Exception as e:
            logger.debug("nmcli restore failed (%s), ignoring.", e)

    def create_virtual_ap(self, physical_iface: str) -> None:
        self._remove_virtual_iface()
        run_sudo_checked(["iw", "dev", physical_iface, "interface", "add",
                          self.virtual_iface, "type", "__ap"])
        logger.info("Created virtual AP interface %s on %s.", self.virtual_iface, physical_iface)

    def generate_config(self, config: AppConfig, channel: str) -> str:
        template = self.env.get_template("hostapd.conf.j2")
        rendered = template.render(
            interface=self.virtual_iface,
            ssid=config.ssid,
            password=config.password,
            security=config.security,
            channel=channel
        )
        # Verify the channel actually made it into the rendered config.
        # If the Jinja2 template has channel hardcoded, patch it here.
        if f"channel={channel}" not in rendered:
            logger.warning(
                "Template did not render channel=%s — patching config directly.", channel
            )
            rendered = re.sub(r'(?m)^channel=\d+', f'channel={channel}', rendered)
            if f"channel={channel}" not in rendered:
                rendered += f"\nchannel={channel}"
        return rendered

    def start(self, config: AppConfig) -> None:
        channel = self._get_current_channel(config.interface)

        # Create the virtual interface BEFORE telling NM anything.
        # NM will see the new interface and try to manage it — we immediately
        # tell NM to leave cord-ap0 alone. We do NOT touch wlp1s0 at all:
        # setting wlp1s0 unmanaged kills your existing internet connection.
        self.create_virtual_ap(config.interface)

        # Immediately set cord-ap0 unmanaged so NM doesn't fight hostapd.
        # This must happen before hostapd starts, otherwise NM grabs wpa_supplicant
        # on cord-ap0 and hostapd loses the interface 10 seconds later.
        self._set_nm_unmanaged(self.virtual_iface)

        content = self.generate_config(config, channel)
        CONF_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONF_FILE.write_text(content)
        logger.debug("hostapd config written to %s:\n%s", CONF_FILE, content)

        self.systemd.create_service(
            unit_name=SERVICE_NAME,
            exec_start=f"/usr/sbin/hostapd {CONF_FILE}",
            description="CordonNet Virtual AP"
        )
        self.systemd.start_service(SERVICE_NAME)

    def stop(self, config: AppConfig) -> None:
        self.systemd.stop_service(SERVICE_NAME)
        if CONF_FILE.exists():
            CONF_FILE.unlink()
        # Return cord-ap0 to NM before removing it so NM state machine is clean
        self._set_nm_managed(self.virtual_iface)
        self._remove_virtual_iface()
        # wlp1s0 was never touched — NM still owns it, internet stays alive.