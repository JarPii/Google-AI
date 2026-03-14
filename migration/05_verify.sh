#!/bin/bash
# =============================================================================
# Vaihe 5: Tarkista asennus
# Varmistaa että kaikki komponentit toimivat
# =============================================================================

echo "=========================================="
echo "  Vaihe 5: Asennuksen tarkistus"
echo "=========================================="
echo ""

ERRORS=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✅ $name"
  else
    echo "  ❌ $name"
    ((ERRORS++))
  fi
}

echo "--- Järjestelmäpaketit ---"
check "Git $(git --version 2>/dev/null | cut -d' ' -f3)" "command -v git"
check "Python3 $(python3 --version 2>/dev/null | cut -d' ' -f2)" "command -v python3"
check "Node.js $(node --version 2>/dev/null)" "command -v node"
check "npm $(npm --version 2>/dev/null)" "command -v npm"
check "Docker $(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+')" "command -v docker"
check "Docker Compose" "docker compose version"
check "Azure CLI $(az version 2>/dev/null | grep -oP '\"azure-cli\": \"\K[^\"]+' )" "command -v az"
check "Google Chrome" "command -v google-chrome"

echo ""
echo "--- Dev-työkalut ---"
check "VS Code" "command -v code"
check "DBeaver" "snap list dbeaver-ce"
check "Draw.io" "snap list drawio"
check "Typora" "snap list typora"
check "Wireshark" "command -v wireshark"
check "rclone" "command -v rclone"

echo ""
echo "--- VS Code extensionit ---"
EXPECTED_EXTENSIONS=(
  "github.copilot"
  "github.copilot-chat"
  "ms-python.python"
  "ms-azuretools.vscode-docker"
  "ms-toolsai.jupyter"
  "serhioromano.vscode-st"
)
INSTALLED_EXT=$(code --list-extensions 2>/dev/null)
for ext in "${EXPECTED_EXTENSIONS[@]}"; do
  if echo "$INSTALLED_EXT" | grep -qi "$ext"; then
    echo "  ✅ $ext"
  else
    echo "  ❌ $ext"
    ((ERRORS++))
  fi
done

echo ""
echo "--- Levyt ---"
check "HDD mountattu /mnt/hdd" "mountpoint -q /mnt/hdd"
check "SSD on root-levy" "[ $(df / | tail -1 | awk '{print $1}') != '/dev/sda4' ]"

echo ""
echo "--- Tämä projekti (Google AI) ---"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

check "Git repo" "git -C '$PROJECT_DIR' status"
check ".env löytyy" "[ -f '$PROJECT_DIR/.env' ]"
check "Python venv" "[ -d '$PROJECT_DIR/.venv' ]"
check "requirements.txt asennettu" "'$PROJECT_DIR/.venv/bin/python' -c 'import fastapi'"

echo ""
echo "--- Docker-kontit ---"
if command -v docker &>/dev/null && docker info &>/dev/null; then
  cd "$PROJECT_DIR"
  RUNNING=$(docker compose ps --status running -q 2>/dev/null | wc -l)
  if [ "$RUNNING" -ge 2 ]; then
    echo "  ✅ Docker-kontit käynnissä ($RUNNING kpl)"
    docker compose ps --format "table {{.Name}}\t{{.Status}}"
  else
    echo "  ❌ Docker-kontit eivät käynnissä ($RUNNING/2)"
    ((ERRORS++))
  fi
else
  echo "  ⚠️  Docker ei saatavilla (logout+login?)"
  ((ERRORS++))
fi

echo ""
echo "--- Git config ---"
GIT_NAME=$(git config --global user.name 2>/dev/null)
GIT_EMAIL=$(git config --global user.email 2>/dev/null)
if [ -n "$GIT_NAME" ]; then
  echo "  ✅ Git user: $GIT_NAME <$GIT_EMAIL>"
else
  echo "  ❌ Git user ei konfiguroitu"
  ((ERRORS++))
fi

echo ""
echo "=========================================="
if [ "$ERRORS" -eq 0 ]; then
  echo "  🎉 Kaikki OK! Migraatio onnistui!"
else
  echo "  ⚠️  $ERRORS ongelmaa löytyi — tarkista yllä"
fi
echo "=========================================="
echo ""
echo "Levy-info:"
df -h / /mnt/hdd 2>/dev/null | tail -2
echo ""
