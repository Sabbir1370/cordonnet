"""Handle low-level networking operations (ip link/addr)."""
import logging
from cordonnet.utils.shell import run_sudo_checked

logger = logging.getLogger("cordonnet.app")

class NetworkManager:
    @staticmethod
    def set_ip(interface: str, ip_cidr: str) -> None:
        """Assign an IP address to an interface."""
        run_sudo_checked(["ip", "addr", "add", ip_cidr, "dev", interface])

    @staticmethod
    def set_up(interface: str) -> None:
        """Bring interface up."""
        run_sudo_checked(["ip", "link", "set", interface, "up"])

    @staticmethod
    def set_down(interface: str) -> None:
        run_sudo_checked(["ip", "link", "set", interface, "down"])

    @staticmethod
    def get_interface_status(interface: str) -> str:
        """Return 'UP' or 'DOWN'."""
        from cordonnet.utils.shell import run_checked
        output = run_checked(["ip", "-o", "link", "show", interface])
        if "state UP" in output:
            return "UP"
        return "DOWN"