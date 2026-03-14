#!/bin/bash
# =============================================================================
# Vaihe 1: Järjestelmäpaketit
# Asentaa: Docker, Node.js 20, Chrome, Azure CLI, perustyökalut
# =============================================================================
set -e

echo "=========================================="
echo "  Vaihe 1: Järjestelmäpaketit"
echo "=========================================="

# --- Päivitykset ---
echo "[1/6] Päivitetään pakettilistaukset..."
sudo apt update && sudo apt upgrade -y

# --- Perustyökalut ---
echo "[2/6] Asennetaan perustyökalut..."
sudo apt install -y \
  git curl wget unzip \
  python3-pip python3-venv python3-dev \
  libpq-dev build-essential \
  software-properties-common ca-certificates gnupg \
  wireshark gimp audacity gparted \
  tesseract-ocr tesseract-ocr-fin \
  imagemagick handbrake rclone \
  language-pack-fi language-pack-gnome-fi

# --- Docker ---
echo "[3/6] Asennetaan Docker..."
if ! command -v docker &>/dev/null; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt update
  sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "$USER"
  echo "  ✅ Docker asennettu (logout+login aktivoi docker-ryhmän)"
else
  echo "  ⏭️  Docker on jo asennettuna"
fi

# --- Node.js 20 ---
echo "[4/6] Asennetaan Node.js 20..."
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt install -y nodejs
  echo "  ✅ Node.js $(node --version) asennettu"
else
  echo "  ⏭️  Node.js $(node --version) on jo asennettuna"
fi

# --- Google Chrome ---
echo "[5/6] Asennetaan Google Chrome..."
if ! command -v google-chrome &>/dev/null; then
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O /tmp/chrome.deb
  sudo dpkg -i /tmp/chrome.deb || sudo apt install -f -y
  rm /tmp/chrome.deb
  echo "  ✅ Chrome asennettu"
else
  echo "  ⏭️  Chrome on jo asennettuna"
fi

# --- Azure CLI ---
echo "[6/6] Asennetaan Azure CLI..."
if ! command -v az &>/dev/null; then
  curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
  echo "  ✅ Azure CLI asennettu"
else
  echo "  ⏭️  Azure CLI $(az version --query '"azure-cli"' -o tsv) on jo asennettuna"
fi

echo ""
echo "=========================================="
echo "  ✅ Vaihe 1 valmis!"
echo "=========================================="
echo ""
echo "⚠️  HUOM: Kirjaudu ulos ja takaisin (tai reboot)"
echo "  jotta docker-ryhmä aktivoituu!"
echo ""
