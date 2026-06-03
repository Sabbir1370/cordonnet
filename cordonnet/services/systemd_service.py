"""Manage transient systemd services for hostapd and dnsmasq."""
import logging
from pathlib import Path
from cordonnet.utils.shell import run_sudo_checked, ShellError

logger = logging.getLogger("cordonnet.app")

class SystemdServiceManager:
    """Creates, starts, stops and removes transient systemd units."""
    UNIT_DIR = Path("/run/systemd/system")

    @staticmethod
    def _service_file_path(unit_name: str) -> Path:
        return SystemdServiceManager.UNIT_DIR / f"{unit_name}.service"

    @staticmethod
    def create_service(unit_name: str, exec_start: str, description: str = "", restart: str = "no") -> None:
        """Write a transient service unit file."""
        unit_content = f"""[Unit]
Description={description}
After=network.target

[Service]
Type=simple
ExecStart={exec_start}
Restart={restart}

[Install]
WantedBy=multi-user.target
"""
        path = SystemdServiceManager._service_file_path(unit_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(unit_content)
        logger.info("Created transient service unit: %s", path)

    @staticmethod
    def start_service(unit_name: str) -> None:
        """Enable (if needed) and start the service."""
        try:
            run_sudo_checked(["systemctl", "daemon-reload"])
            run_sudo_checked(["systemctl", "start", unit_name])
            logger.info("Started service: %s", unit_name)
        except ShellError as e:
            logger.error("Failed to start %s: %s", unit_name, e)
            raise

    @staticmethod
    def stop_service(unit_name: str) -> None:
        """Stop and remove the service unit."""
        try:
            run_sudo_checked(["systemctl", "stop", unit_name])
        except ShellError:
            logger.warning("Service %s already stopped or failed.", unit_name)
        try:
            run_sudo_checked(["systemctl", "disable", unit_name])
        except ShellError:
            pass
        path = SystemdServiceManager._service_file_path(unit_name)
        if path.exists():
            path.unlink()
            run_sudo_checked(["systemctl", "daemon-reload"])
            logger.info("Removed transient unit: %s", unit_name)

    @staticmethod
    def is_active(unit_name: str) -> bool:
        """Check if the service is active."""
        try:
            result = run_sudo_checked(["systemctl", "is-active", unit_name])
            return result.strip() == "active"
        except ShellError:
            return False