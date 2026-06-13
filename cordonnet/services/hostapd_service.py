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

    def _get_current_channel(self, physical_iface: str):
        """Return (channel, hw_mode) matching the physical interface frequency."""
        try:
            out = run_sudo_checked(["iw", "dev", physical_iface, "info"])
            match = re.search(r'channel\s+(\d+)', out)
            if match:
                channel = match.group(1)
                hw_mode = "a" if int(channel) >= 36 else "g"
                logger.info("Detected channel %s (%s GHz) on %s.",
                            channel, "5" if hw_mode == "a" else "2.4", physical_iface)
                return channel, hw_mode
        except Exception as e:
            logger.warning("Could not detect channel on %s: %s. Defaulting to ch6/2.4GHz.", physical_iface, e)
        return "6", "g"

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

    def generate_config(self, config: AppConfig, channel: str, hw_mode: str) -> str:
        template = self.env.get_template("hostapd.conf.j2")
        rendered = template.render(
            interface=self.virtual_iface,
            ssid=config.ssid,
            password=config.password,
            security=config.security,
            channel=channel,
            hw_mode=hw_mode
        )
        # Safety patch: ensure channel and hw_mode match reality
        if f"channel={channel}" not in rendered:
            logger.warning("Patching channel=%s into config.", channel)
            rendered = re.sub(r'(?m)^channel=\d+', f'channel={channel}', rendered)
            if f"channel={channel}" not in rendered:
                rendered += f"\nchannel={channel}"
        if f"hw_mode={hw_mode}" not in rendered:
            logger.warning("Patching hw_mode=%s into config.", hw_mode)
            rendered = re.sub(r'(?m)^hw_mode=\w+', f'hw_mode={hw_mode}', rendered)
            if f"hw_mode={hw_mode}" not in rendered:
                rendered += f"\nhw_mode={hw_mode}"
        return rendered

    def _ensure_nm_conf(self) -> None:
        """Write the NetworkManager unmanaged-devices conf if not already present."""
        conf_path = Path("/etc/NetworkManager/conf.d/cordonnet.conf")
        if conf_path.exists():
            return
        nm_conf = "[keyfile]\nunmanaged-devices=interface-name:cord-ap0\n"
        try:
            # Write via tee so sudo can create the file
            run_sudo_checked(["bash", "-c",
                f"printf '%s' {nm_conf!r} > {conf_path}"])
            run_sudo_checked(["systemctl", "reload", "NetworkManager"])
            logger.info("Created %s and reloaded NetworkManager.", conf_path)
        except Exception as e:
            logger.warning("Could not write NM conf: %s — falling back to nmcli.", e)

    def start(self, config: AppConfig) -> None:
        self._ensure_nm_conf()
        channel, hw_mode = self._get_current_channel(config.interface)

        # Create the virtual interface BEFORE telling NM anything.
        # NM will see the new interface and try to manage it — we immediately
        # tell NM to leave cord-ap0 alone. We do NOT touch wlp1s0 at all:
        # setting wlp1s0 unmanaged kills your existing internet connection.
        self.create_virtual_ap(config.interface)

        # NM is permanently configured to ignore cord-ap0 via
        # /etc/NetworkManager/conf.d/cordonnet.conf (unmanaged-devices=interface-name:cord-ap0).
        # The runtime nmcli call is kept as a fallback in case the conf file is missing.
        self._set_nm_unmanaged(self.virtual_iface)

        content = self.generate_config(config, channel, hw_mode)
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