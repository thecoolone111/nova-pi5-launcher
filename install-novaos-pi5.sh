#!/usr/bin/env bash
# ================================================================
#  Nova OS v6  —  Raspberry Pi 5 Installer
#  Raspberry Pi OS Trixie/Bookworm 64-bit (ARM64)
#
#  One line install:
#    curl -sSL tinyurl.com/YOUR-TINYURL | bash
#
#  Or manually:
#    chmod +x install-novaos-pi5.sh && ./install-novaos-pi5.sh
# ================================================================

set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m';  BOLD='\033[1m';     NC='\033[0m'
step() { echo -e "\n${CYAN}${BOLD}▶  $1${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC}  $1"; }
info() { echo -e "  ${CYAN}→${NC}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
die()  { echo -e "\n${RED}✗  $1${NC}\n"; exit 1; }

clear
echo -e "${CYAN}${BOLD}"
echo "  ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗      ██████╗ ███████╗"
echo "  ████╗  ██║██╔═══██╗██║   ██║██╔══██╗    ██╔═══██╗██╔════╝"
echo "  ██╔██╗ ██║██║   ██║██║   ██║███████║    ██║   ██║███████╗"
echo "  ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║    ██║   ██║╚════██║"
echo "  ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║    ╚██████╔╝███████║"
echo "  ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝     ╚═════╝ ╚══════╝"
echo -e "  v6.0  ·  Raspberry Pi 5  ·  ARM64  ·  Native PyQt6 App${NC}"
echo ""

# ── Guards ───────────────────────────────────────────────────────
[[ $(uname -m) == "aarch64" ]]  || die "ARM64 only. Got: $(uname -m)"
[[ $EUID -ne 0 ]]               || die "Run as your normal user, not root."
command -v apt-get &>/dev/null  || die "apt-get not found — Raspberry Pi OS required."

CODENAME=$(lsb_release -cs 2>/dev/null || echo bookworm)
[[ "$CODENAME" == "bookworm" || "$CODENAME" == "trixie" ]] && ok "Raspberry Pi OS $CODENAME detected" \
  || warn "Expected Bookworm/Trixie, got: $CODENAME — continuing"

# ── Paths ─────────────────────────────────────────────────────────
APP_DIR="/opt/novaos"
PYTHON_APP="$APP_DIR/novaos.py"
LAUNCH_BIN="/usr/local/bin/novaos"
EGLFS="$HOME/eglfs.json"
DESKTOP_APPS="/usr/share/applications/novaos.desktop"
DESKTOP_LINK="$HOME/Desktop/NovaOS.desktop"
AUTOSTART="$HOME/.config/autostart/novaos.desktop"

echo ""

# ════════════════════════════════════════════════════════════════
#  PHASE 1 — System packages
# ════════════════════════════════════════════════════════════════
step "Updating package lists"
sudo apt-get update -qq
ok "Done"

step "Python 3 + PyQt6 (native app framework)"
sudo apt-get install -y python3 python3-pip python3-venv python3-pyqt6
ok "PyQt6 installed"

step "Python extras (psutil for live stats)"
# Bookworm blocks system pip — must use venv
sudo mkdir -p "$APP_DIR"
sudo python3 -m venv "$APP_DIR/venv"
sudo "$APP_DIR/venv/bin/pip" install --quiet psutil requests flask
ok "psutil + requests + flask installed in $APP_DIR/venv"

step "RetroArch emulator"
if ! command -v retroarch &>/dev/null; then
  sudo apt-get install -y retroarch && ok "Installed"
else
  ok "Already installed"
fi
for sys in ps1 psp nes snes n64 gba nds genesis dreamcast arcade gameboy gbc 3ds atari2600 segacd; do
  mkdir -p "$HOME/RetroPie/roms/$sys"
done
mkdir -p "$HOME/RetroPie/BIOS"
ok "ROM directories ready at ~/RetroPie/roms/"

step "Moonlight game streaming"
if ! command -v moonlight-qt &>/dev/null; then
  curl -1sLf \
    'https://dl.cloudsmith.io/public/moonlight-game-streaming/moonlight-qt/setup.deb.sh' \
    | distro=raspbian codename="$CODENAME" sudo -E bash
  sudo apt-get install -y moonlight-qt && ok "Installed"
else
  ok "Already installed"
fi
if [[ ! -f "$EGLFS" ]]; then
  echo '{ "device": "/dev/dri/card1" }' > "$EGLFS"
  ok "Created eglfs.json (Pi 5 DRM fix)"
fi
sudo tee /usr/local/bin/moonlight-nova >/dev/null <<'WRAP'
#!/usr/bin/env bash
EGLFS="$HOME/eglfs.json"
if [[ -n "${DISPLAY:-}" ]] || [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
  exec moonlight-qt "$@"
else
  exec env QT_QPA_EGLFS_KMS_CONFIG="$EGLFS" moonlight-qt "$@"
fi
WRAP
sudo chmod +x /usr/local/bin/moonlight-nova
ok "moonlight-nova wrapper installed"

step "Vesktop — Discord for ARM64"
if ! command -v vesktop &>/dev/null; then
  TAG=$(curl -sf https://api.github.com/repos/Vencord/Vesktop/releases/latest \
        | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/' || true)
  if [[ -n "$TAG" ]]; then
    TMP=$(mktemp /tmp/vesktop-XXXXXX.deb)
    if wget -q -O "$TMP" "https://github.com/Vencord/Vesktop/releases/download/v${TAG}/vesktop_${TAG}_arm64.deb"; then
      sudo apt-get install -y "$TMP" && ok "Vesktop v$TAG installed"
    else
      warn "Download failed — install manually from github.com/Vencord/Vesktop/releases"
    fi
    rm -f "$TMP"
  else
    warn "Could not reach GitHub — install manually from github.com/Vencord/Vesktop/releases"
  fi
else
  ok "Already installed"
fi

step "Raspotify — Spotify Connect"
if ! systemctl list-unit-files raspotify.service &>/dev/null; then
  sudo apt-get install -y curl
  curl -sL https://dtcooper.github.io/raspotify/install.sh | sh
  if [[ -f /etc/raspotify.conf ]] && ! grep -q '^LIBRESPOT_NAME=' /etc/raspotify.conf; then
    printf '\nLIBRESPOT_NAME="Nova OS Pi5"\nLIBRESPOT_BITRATE="320"\n' \
      | sudo tee -a /etc/raspotify.conf >/dev/null
    sudo systemctl restart raspotify
  fi
  ok "Raspotify installed — device: 'Nova OS Pi5'"
else
  ok "Already installed"
fi

# ════════════════════════════════════════════════════════════════
#  PHASE 2 — Stats server
# ════════════════════════════════════════════════════════════════
step "Stats server (CPU temp / RAM / disk for Nova OS)"
sudo tee "$APP_DIR/stats_server.py" >/dev/null <<'PY'
#!/usr/bin/env python3
import psutil
from flask import Flask, jsonify
app = Flask(__name__)

def cpu_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            return round(int(f.read()) / 1000, 1)
    except Exception:
        pass
    try:
        t = psutil.sensors_temperatures()
        for k in ('cpu_thermal', 'cpu-thermal', 'coretemp'):
            if k in t and t[k]:
                return round(t[k][0].current, 1)
    except Exception:
        pass
    return None

@app.route('/stats')
def stats():
    vm   = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    r = jsonify({
        'cpu_temp':     cpu_temp(),
        'ram_pct':      round(vm.percent, 1),
        'ram_used_gb':  round(vm.used   / 1024**3, 2),
        'ram_total_gb': round(vm.total  / 1024**3, 2),
        'disk_pct':     round(disk.percent, 1),
        'disk_used_gb': round(disk.used  / 1024**3, 1),
        'disk_total_gb':round(disk.total / 1024**3, 1),
    })
    r.headers['Access-Control-Allow-Origin'] = '*'
    return r

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=7777, debug=False)
PY

sudo tee /etc/systemd/system/novaos-stats.service >/dev/null <<SVC
[Unit]
Description=Nova OS Stats Server
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/stats_server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SVC
sudo systemctl daemon-reload
sudo systemctl enable --now novaos-stats.service
ok "Stats server running (novaos-stats.service)"

# ════════════════════════════════════════════════════════════════
#  PHASE 3 — Install the Python app
# ════════════════════════════════════════════════════════════════
step "Installing Nova OS native app (PyQt6)"

GITHUB_RAW="https://raw.githubusercontent.com/thecoolone111/nova-pi5-launcher/main"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/novaos.py" ]]; then
  sudo cp "$SCRIPT_DIR/novaos.py" "$PYTHON_APP"
  ok "Copied novaos.py from $SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/novaos(1).py" ]]; then
  sudo cp "$SCRIPT_DIR/novaos(1).py" "$PYTHON_APP"
  ok "Copied novaos(1).py from $SCRIPT_DIR"
else
  info "Downloading novaos.py from GitHub..."
  sudo curl -fsSL "$GITHUB_RAW/novaos.py" -o "$PYTHON_APP" 2>/dev/null || \
  sudo curl -fsSL "$GITHUB_RAW/novaos(1).py" -o "$PYTHON_APP" 2>/dev/null || \
  die "Could not download novaos.py — check your internet connection or visit github.com/thecoolone111/nova-pi5-launcher"
  ok "Downloaded novaos.py from GitHub"
fi
sudo chmod +x "$PYTHON_APP"

# ── Launch command ─────────────────────────────────────────────
sudo tee "$LAUNCH_BIN" >/dev/null <<LAUNCHER
#!/usr/bin/env bash
# Nova OS v5 — native PyQt6 launcher
# Uses the venv Python so PyQt6/psutil are always available
exec $APP_DIR/venv/bin/python $PYTHON_APP "\$@"
LAUNCHER
sudo chmod +x "$LAUNCH_BIN"
ok "'novaos' command installed — type it anywhere to launch"

# ── .desktop file ──────────────────────────────────────────────
ICON="input-gaming"
for i in /usr/share/pixmaps/retroarch.png \
          /usr/share/icons/hicolor/256x256/apps/org.mozilla.firefox.png; do
  [[ -f "$i" ]] && { ICON="$i"; break; }
done

DESK="[Desktop Entry]
Version=1.0
Type=Application
Name=Nova OS
GenericName=Gaming Launcher
Comment=Raspberry Pi 5 Gaming OS — Native PyQt6
Exec=$LAUNCH_BIN
Icon=$ICON
Terminal=false
StartupNotify=true
Categories=Game;Emulator;
Keywords=gaming;launcher;retro;stream;"

echo "$DESK" | sudo tee "$DESKTOP_APPS" >/dev/null
sudo chmod 644 "$DESKTOP_APPS"
mkdir -p "$HOME/Desktop"
echo "$DESK" > "$DESKTOP_LINK"
chmod +x "$DESKTOP_LINK"
ok "App menu entry: App Menu → Games → Nova OS"
ok "Desktop shortcut created"

# ── Installer also in app menu ──────────────────────────────────
sudo tee /usr/share/applications/novaos-installer.desktop >/dev/null <<INSTD
[Desktop Entry]
Version=1.0
Type=Application
Name=Nova OS Installer
Comment=Re-run Nova OS installer / update
Exec=bash -c 'lxterminal -e "bash ${BASH_SOURCE[0]}; read -rp \"Done — press Enter\" _" || xterm -e "bash ${BASH_SOURCE[0]}; read -rp \"Done\" _"'
Icon=system-software-install
Terminal=false
Categories=System;
INSTD
sudo chmod 644 /usr/share/applications/novaos-installer.desktop
ok "Installer in App Menu → System → Nova OS Installer"

# ── Auto-start on login ────────────────────────────────────────
step "Auto-start Nova OS on login"
mkdir -p "$AUTOSTART_DIR" 2>/dev/null || true
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
echo "$DESK" > "$AUTOSTART/novaos.desktop" 2>/dev/null || \
echo "$DESK" > "$AUTOSTART_DIR/novaos.desktop"
ok "Nova OS will launch automatically on every login"

# ════════════════════════════════════════════════════════════════
#  PHASE 4 — Final check
# ════════════════════════════════════════════════════════════════
step "Verifying installation"
sleep 2
curl -sf http://localhost:7777/stats | grep -q 'ram_pct' \
  && ok "Stats server       ✓  :7777" \
  || warn "Stats server       still starting — check: sudo systemctl status novaos-stats"
[[ -f "$PYTHON_APP" ]]   && ok "novaos.py          ✓  $PYTHON_APP"     || warn "novaos.py missing"
[[ -x "$LAUNCH_BIN" ]]   && ok "novaos command     ✓  $LAUNCH_BIN"     || warn "launch binary missing"
command -v moonlight-qt &>/dev/null && ok "Moonlight          ✓" || warn "Moonlight          not found"
command -v vesktop      &>/dev/null && ok "Vesktop            ✓" || warn "Vesktop            not installed"
command -v retroarch    &>/dev/null && ok "RetroArch          ✓" || warn "RetroArch          not found"
systemctl is-active raspotify &>/dev/null \
  && ok "Raspotify          ✓  running" || warn "Raspotify          not running"
$APP_DIR/venv/bin/python -c "import PyQt6.QtWidgets" 2>/dev/null \
  && ok "PyQt6              ✓  in venv" || warn "PyQt6              not found in venv — check install"

# ════════════════════════════════════════════════════════════════
echo ""
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  Nova OS v6 installed — native PyQt6 desktop app!${NC}"
echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}Launch Nova OS:${NC}"
echo -e "  • Terminal   →  ${CYAN}novaos${NC}"
echo -e "  • App menu   →  Games → Nova OS"
echo -e "  • Desktop    →  double-click Nova OS shortcut"
echo -e "  • On reboot  →  launches automatically ✓"
echo ""
echo -e "  ${BOLD}Keys inside Nova OS:${NC}"
echo -e "  • ${CYAN}1-5${NC}       switch tabs"
echo -e "  • ${CYAN}F11${NC}       toggle fullscreen"
echo -e "  • ${CYAN}Ctrl+Q${NC}    quit"
echo -e "  • ${CYAN}Escape${NC}    go home"
echo ""
echo -e "  ${BOLD}Other apps:${NC}"
echo -e "  • Spotify    →  phone: Devices → ${CYAN}Nova OS Pi5${NC}"
echo -e "  • Discord    →  ${CYAN}vesktop${NC}"
echo -e "  • Streaming  →  ${CYAN}moonlight-nova${NC}"
echo ""
echo -e "  ${YELLOW}Reboot recommended to start all services cleanly.${NC}"
echo ""
read -rp "  Reboot now? [y/N] " _r
[[ "${_r,,}" == "y" ]] && sudo reboot || echo -e "\n  ${GREEN}Run ${CYAN}novaos${GREEN} to launch.${NC}\n"
