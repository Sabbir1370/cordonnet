# CordonNet

> A modern Linux utility that spins up a **virtual Wi-Fi hotspot on your existing wireless card** — no USB dongle, no Ethernet cable, no dropped connection.

Your internet stays up while clients connect to the virtual AP. Built for cybersecurity labs, CTFs, workshops, and ad-hoc sharing.

---

## Features

|                            |                                                       |
| -------------------------- | ----------------------------------------------------- |
| 🔁 **Single-interface AP** | Virtual hotspot on the same card you use for internet |
| 🌐 **Internet sharing**    | NAT via `nftables` — one flag, fully automatic        |
| 🔒 **Isolated mode**       | Clients stay local; your machine stays online         |
| 🛡️ **MAC filtering**       | Whitelist or blacklist with optional device labels    |
| 📡 **Client monitor**      | Live list of connected devices — IP, MAC, hostname    |
| ♻️ **Clean teardown**      | Full restore on stop — no reboot, no leftover rules   |
| ⚙️ **Modern stack**        | `hostapd` · `dnsmasq` · `nftables` · `systemd`        |

---

## Requirements

- **OS:** Debian 13+, Parrot OS 6+, Kali 2025+, Ubuntu 24.04+
- **Python:** 3.12 or newer
- **Wi-Fi card:** Must support virtual AP mode (run `cordonnet detect` to check)

Install system dependencies:

```bash
sudo apt install -y hostapd dnsmasq nftables iw iproute2
```

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/cordonnet.git
cd cordonnet
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Verify it works:

```bash
cordonnet --help
```

---

## Setting Your Wireless Interface

CordonNet needs to know which physical Wi-Fi card to use. Do this once after install.

**Step 1 — Find your interface name**

```bash
iw dev
```

Look for a line like `Interface wlp1s0` or `Interface wlan0`. That's your interface name.

**Step 2 — Check AP mode support**

```bash
cordonnet detect
```

Output should say `✓ Virtual AP mode is supported`. If not, your card cannot act as a hotspot.

**Step 3 — Set the interface**

```bash
cordonnet hotspot set-interface wlp1s0
```

Or edit `config/default.yaml` directly:

```yaml
interface: wlp1s0 # replace with your interface name
```

---

## Quick Start

> **All `hotspot start/stop` commands require `sudo`.**  
> Always activate the virtual environment first: `source venv/bin/activate`

```bash
# Start hotspot — internet is shared with connected clients automatically
sudo $(which python) -m cordonnet.main hotspot start

# Start in isolated mode — clients get a LAN only, no internet
sudo $(which python) -m cordonnet.main hotspot start --isolated

# Stop the hotspot — Wi-Fi restored, all rules cleaned up
sudo $(which python) -m cordonnet.main hotspot stop

# Restart (e.g. after changing SSID or password)
sudo $(which python) -m cordonnet.main hotspot restart
```

After installing with `pip install -e .`, root commands can also be run as:

```bash
sudo cordonnet hotspot start
```

---

## Command Reference

### Hotspot lifecycle

| Command                    | Description                            |
| -------------------------- | -------------------------------------- |
| `hotspot start`            | Start virtual AP with internet sharing |
| `hotspot start --isolated` | Start without internet for clients     |
| `hotspot stop`             | Stop hotspot and restore Wi-Fi         |
| `hotspot restart`          | Restart (preserves current mode)       |

### Hotspot settings _(no sudo needed)_

| Command                          | Description                        |
| -------------------------------- | ---------------------------------- |
| `hotspot set-ssid "MyNet"`       | Change the SSID                    |
| `hotspot set-password "pass123"` | Change the Wi-Fi password          |
| `hotspot set-interface wlp1s0`   | Change the base wireless interface |
| `hotspot mode normal`            | Allow all except blacklisted MACs  |
| `hotspot mode whitelist`         | Allow only whitelisted MACs        |

### MAC access control _(no sudo needed)_

```bash
# Whitelist
cordonnet hotspot whitelist-add aa:bb:cc:dd:ee:ff --name "John's Phone"
cordonnet hotspot whitelist-remove aa:bb:cc:dd:ee:ff
cordonnet hotspot whitelist-list

# Blacklist
cordonnet hotspot blacklist-add 00:11:22:33:44:55 --name "Unknown"
cordonnet hotspot blacklist-remove 00:11:22:33:44:55
cordonnet hotspot blacklist-list
```

### Client monitoring _(no sudo needed)_

```bash
cordonnet clients list                    # All connected devices
cordonnet clients lookup 192.168.50.10    # Lookup by IP
cordonnet clients lookup aa:bb:cc:dd:ee:ff  # Lookup by MAC
```

### Status & config _(no sudo needed)_

```bash
cordonnet status           # Live hotspot dashboard
cordonnet config show      # Print current config as YAML
cordonnet config validate  # Check config file for errors
cordonnet detect           # Check if hardware supports virtual AP
```

> The full quick-reference is also available in [cheatSheet.txt](cheatSheet.txt).

---

## Configuration

All settings live in `config/default.yaml`:

```yaml
ssid: CordonCTF
password: changeme123
interface: wlp1s0 # your physical Wi-Fi card
subnet: 192.168.50.0/24
gateway: 192.168.50.1
dhcp:
  start: 192.168.50.10
  end: 192.168.50.100
internet:
  enabled: true # false = isolated by default
security:
  client_isolation: true # clients can't talk to each other
  mode: normal # "normal" (blacklist) or "whitelist"
  whitelist: []
  blacklist: []
```

Changes to SSID, password, and mode take effect on the next `hotspot start/restart`.

---

## How It Works

```
Your Wi-Fi card (wlp1s0)
│
├── stays connected to your router  ←─ internet never drops
│
└── hosts a virtual interface (cord-ap0)
        │
        ├── hostapd    → broadcasts the SSID on the same channel
        ├── dnsmasq    → assigns IPs + DNS to connected clients
        └── nftables   → NAT masquerade (cord-ap0 → wlp1s0)
                         inside a dedicated "cordonnet" table
                         (never touches your existing firewall)
```

On `hotspot stop`: nftables table flushed, `cord-ap0` removed, `ip_forward` restored, NetworkManager regains control — no trace left.

---

## Troubleshooting

**`Too many open files` when starting**  
A stale `cord-ap0` from a previous failed run is still registered. Remove it:

```bash
sudo iw dev cord-ap0 del
```

**SSID not visible on phone**  
NetworkManager may have grabbed `cord-ap0`. Check:

```bash
sudo journalctl -u cordonnet-hotspot -n 20 --no-pager
```

If you see `INTERFACE-DISABLED`, ensure you're using the latest `hostapd_service.py` which sets `cord-ap0` unmanaged before starting hostapd.

**Connected clients have no internet**  
Check reverse-path filtering and ip_forward:

```bash
cat /proc/sys/net/ipv4/ip_forward           # should be 1
sysctl net.ipv4.conf.all.rp_filter          # should be 0 while hotspot runs
```

The latest `nftables_service.py` sets these automatically.

**`cordonnet status` crashes with PermissionError on log file**  
Deploy the latest `cordonnet/utils/logging.py` — it falls back to console logging when run without root.

---

## Project Structure

```
cordonnet/
├── cli/            # Typer CLI commands (hotspot, clients, config, detect, status)
├── core/           # Business logic (hotspot, client, config, network managers)
├── models/         # Pydantic models (AppConfig, Client, HotspotStatus)
├── services/       # System service wrappers (hostapd, dnsmasq, nftables, systemd)
├── templates/      # Jinja2 config templates (hostapd.conf.j2, dnsmasq.conf.j2)
└── utils/          # Shell, logging, validation, hardware detection
config/
└── default.yaml    # Default configuration
```

---

## License

MIT — do whatever you want, just don't blame us if your router catches fire.
