#!/bin/bash
# =============================================================================
# Vaihe 2: Dev-työkalut
# Asentaa: Snap-ohjelmat, VS Code extensionit, Git config
# =============================================================================
set -e

echo "=========================================="
echo "  Vaihe 2: Dev-työkalut"
echo "=========================================="

# --- Snap-ohjelmat ---
echo "[1/3] Asennetaan Snap-ohjelmat..."

SNAPS=(
  "dbeaver-ce"
  "drawio"
  "typora"
)

for snap in "${SNAPS[@]}"; do
  if snap list "$snap" &>/dev/null; then
    echo "  ⏭️  $snap on jo asennettuna"
  else
    echo "  📦 Asennetaan $snap..."
    sudo snap install "$snap" --classic 2>/dev/null || sudo snap install "$snap"
  fi
done

# --- VS Code extensionit ---
echo "[2/3] Asennetaan VS Code extensionit..."

EXTENSIONS=(
  "github.copilot"
  "github.copilot-chat"
  "mechatroner.rainbow-csv"
  "ms-azuretools.vscode-containers"
  "ms-azuretools.vscode-docker"
  "ms-ossdata.vscode-pgsql"
  "ms-python.python"
  "ms-python.vscode-pylance"
  "ms-python.vscode-python-envs"
  "ms-python.debugpy"
  "ms-toolsai.jupyter"
  "ms-toolsai.jupyter-keymap"
  "ms-toolsai.jupyter-renderers"
  "ms-toolsai.vscode-jupyter-cell-tags"
  "ms-toolsai.vscode-jupyter-slideshow"
  "serhioromano.vscode-st"
)

for ext in "${EXTENSIONS[@]}"; do
  echo "  📦 $ext"
  code --install-extension "$ext" --force 2>/dev/null || echo "  ⚠️  Ei voitu asentaa: $ext"
done

# --- Git config ---
echo "[3/3] Konfiguroidaan Git..."
git config --global user.name "Jarmo Piipponen"
git config --global user.email "jarmo_piipponen@hotmail.com"
echo "  ✅ Git user: $(git config --global user.name) <$(git config --global user.email)>"

echo ""
echo "=========================================="
echo "  ✅ Vaihe 2 valmis!"
echo "=========================================="
