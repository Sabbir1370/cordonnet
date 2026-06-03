"""High-level hotspot orchestrator – single-interface virtual AP."""
import logging
import time
from cordonnet.models.config import AppConfig
from cordonnet.services.hostapd_service import HostapdService, VIRTUAL_IFACE
from cordonnet.services.dnsmasq_service import DnsmasqService
from cordonnet.services.nftables_service import NftablesService
from cordonnet.utils.shell import run_sudo_checked

logger = logging.getLogger("cordonnet.hotspot")

# Runtime state file — persists across Python instances so stop() knows the mode
import json
from pathlib import Path
_STATE_FILE = Path("/run/cordonnet/state.json")

def _save_state(isolated: bool) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps({"isolated": isolated}))

def _load_state() -> dict:
    try:
        return json.loads(_STATE_FILE.read_text())
    except Exception:
        return {"isolated": False}

def _clear_state() -> None:
    try:
        _STATE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


class HotspotManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.hostapd = HostapdService()
        self.dnsmasq = DnsmasqService()
        self.nft = NftablesService()

    def start(self, isolated: bool = False) -> None:
        """Start virtual AP hotspot with rollback on failure."""
        started_hostapd = False
        assigned_ip = False

        try:
            # 1. Create virtual AP and start hostapd
            self.hostapd.start(self.config)
            started_hostapd = True

            # 2. Assign gateway IP to virtual interface and bring it up
            run_sudo_checked(["ip", "addr", "add", f"{self.config.gateway}/24", "dev", VIRTUAL_IFACE])
            run_sudo_checked(["ip", "link", "set", VIRTUAL_IFACE, "up"])
            assigned_ip = True

            # 3. Start dnsmasq DHCP/DNS (temporarily reflect isolated flag in config)
            original_internet = self.config.internet.enabled
            if isolated:
                self.config.internet.enabled = False
            try:
                self.dnsmasq.start(self.config)
            finally:
                self.config.internet.enabled = original_internet

            # 4. NAT / internet sharing — only when NOT isolated
            if not isolated:
                self.nft.enable_internet(self.config.interface, self.config.subnet)

            # Persist mode so stop() can behave correctly
            _save_state(isolated=isolated)
            logger.info("Hotspot started (isolated=%s).", isolated)

        except Exception:
            logger.exception("Hotspot start failed — rolling back.")
            # Best-effort cleanup in reverse order
            try:
                self.dnsmasq.stop()
            except Exception:
                pass
            if assigned_ip:
                try:
                    run_sudo_checked(["ip", "addr", "del", f"{self.config.gateway}/24", "dev", VIRTUAL_IFACE])
                except Exception:
                    pass
            if started_hostapd:
                try:
                    self.hostapd.stop(self.config)
                except Exception:
                    pass
            raise

    def stop(self) -> None:
        """Stop hotspot and fully restore original Wi‑Fi."""
        state = _load_state()
        was_isolated = state.get("isolated", False)

        # Stop dnsmasq
        self.dnsmasq.stop()

        # Disable NAT only if we enabled it
        if not was_isolated:
            self.nft.disable_internet(self.config.interface, self.config.subnet)

        # Remove gateway IP from virtual interface
        try:
            run_sudo_checked(["ip", "addr", "del", f"{self.config.gateway}/24", "dev", VIRTUAL_IFACE])
        except Exception:
            pass

        # Stop hostapd and remove virtual AP
        self.hostapd.stop(self.config)

        _clear_state()
        logger.info("Hotspot stopped and original Wi‑Fi restored.")

    def restart(self, isolated: bool = False) -> None:
        self.stop()
        time.sleep(1)
        self.start(isolated=isolated)