"""Manage nftables rules for the cordonnet table."""
import logging
from cordonnet.utils.shell import run_sudo_checked, ShellError

logger = logging.getLogger("cordonnet.app")

TABLE_NAME = "cordonnet"
CHAIN_POSTROUTING = "postrouting"
CHAIN_FORWARD = "forward"

class NftablesService:
    @staticmethod
    def _ensure_table():
        try:
            run_sudo_checked(["nft", "add", "table", "ip", TABLE_NAME])
        except ShellError:
            pass

    @staticmethod
    def setup_hotspot_rules(subnet: str, interface: str) -> None:
        pass

    @staticmethod
    def enable_internet(outgoing_interface: str, subnet: str) -> None:
        NftablesService._ensure_table()

        # NAT chain: masquerade AP traffic leaving on the physical interface
        try:
            run_sudo_checked(["nft", "add", "chain", "ip", TABLE_NAME, CHAIN_POSTROUTING,
                              "{ type nat hook postrouting priority srcnat; }"])
        except ShellError:
            pass

        # Forward chain: allow forwarding in both directions
        try:
            run_sudo_checked(["nft", "add", "chain", "ip", TABLE_NAME, CHAIN_FORWARD,
                              "{ type filter hook forward priority filter; }"])
        except ShellError:
            pass

        # Masquerade: AP subnet traffic going out via physical interface
        masq_rule = f"ip saddr {subnet} oifname {outgoing_interface} masquerade"
        try:
            run_sudo_checked(["nft", "add", "rule", "ip", TABLE_NAME, CHAIN_POSTROUTING, masq_rule])
        except ShellError:
            logger.warning("Masquerade rule might already exist.")

        # Forward: allow traffic FROM cord-ap0 TO physical interface (AP -> internet)
        forward_out = f"iifname \"cord-ap0\" oifname \"{outgoing_interface}\" accept"
        try:
            run_sudo_checked(["nft", "add", "rule", "ip", TABLE_NAME, CHAIN_FORWARD, forward_out])
        except ShellError:
            pass

        # Forward: allow established/related return traffic (internet -> AP)
        forward_in = f"iifname \"{outgoing_interface}\" oifname \"cord-ap0\" ct state established,related accept"
        try:
            run_sudo_checked(["nft", "add", "rule", "ip", TABLE_NAME, CHAIN_FORWARD, forward_in])
        except ShellError:
            pass

        # Enable kernel IP forwarding
        run_sudo_checked(["sysctl", "-w", "net.ipv4.ip_forward=1"])

        # Disable reverse-path filtering on both interfaces.
        # rp_filter=1 (default) drops packets where the source IP is not reachable
        # via the interface they arrived on — this kills NAT traffic from cord-ap0
        # because the kernel sees 192.168.50.x packets leaving wlp1s0 and rejects them.
        for iface in ("cord-ap0", outgoing_interface):
            try:
                run_sudo_checked(["sysctl", "-w", f"net.ipv4.conf.{iface}.rp_filter=0"])
            except Exception as e:
                logger.warning("Could not set rp_filter=0 on %s: %s", iface, e)

        logger.info("Internet sharing enabled via nftables (NAT + forward rules).")

    @staticmethod
    def disable_internet(outgoing_interface: str, subnet: str) -> None:
        """Flush and remove cordonnet nftables table, restore ip_forward."""
        try:
            # Delete the entire table — cleaner than flushing chains individually
            run_sudo_checked(["nft", "delete", "table", "ip", TABLE_NAME])
            logger.info("Removed cordonnet nftables table.")
        except ShellError:
            logger.debug("No cordonnet table to remove (may not have been in internet mode).")

        # Disable kernel IP forwarding
        try:
            run_sudo_checked(["sysctl", "-w", "net.ipv4.ip_forward=0"])
        except ShellError:
            logger.warning("Could not reset ip_forward.")

        # Restore rp_filter to default (1) on both interfaces
        for iface in (outgoing_interface, "cord-ap0"):
            try:
                run_sudo_checked(["sysctl", "-w", f"net.ipv4.conf.{iface}.rp_filter=1"])
            except Exception:
                pass

    @staticmethod
    def remove_all_cordonnet_rules() -> None:
        try:
            run_sudo_checked(["nft", "delete", "table", "ip", TABLE_NAME])
        except ShellError:
            logger.info("No cordonnet table to remove.")