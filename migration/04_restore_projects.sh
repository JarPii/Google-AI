#!/bin/bash
# =============================================================================
# Vaihe 4: Projektien palautus
# Kopioi .env-tiedostot, luo venvit, käynnistää Docker-kontit
# =============================================================================
set -e

echo "=========================================="
echo "  Vaihe 4: Projektien palautus"
echo "=========================================="

OLD_HOME="/mnt/hdd/home/jarpii"
NEW_DEV="$HOME/Dev"

# --- Tarkista että HDD on mountattu ---
if [ ! -d "$OLD_HOME" ]; then
  echo "  ❌ HDD ei ole mountattu ($OLD_HOME ei löydy)"
  echo "  Aja ensin: bash migration/03_mount_hdd.sh"
  exit 1
fi

# --- Kopioi .env-tiedostot ---
echo "[1/4] Kopioidaan .env-tiedostot vanhasta asennuksesta..."

# Etsi kaikki .env-tiedostot vanhasta Dev-kansiosta
find "$OLD_HOME/Dev" -maxdepth 2 -name ".env" -type f 2>/dev/null | while read -r envfile; do
  # Rakenna vastaava polku uudessa Devissä
  relative="${envfile#$OLD_HOME/Dev/}"
  target="$NEW_DEV/$relative"
  target_dir=$(dirname "$target")

  if [ -d "$target_dir" ]; then
    if [ ! -f "$target" ]; then
      cp "$envfile" "$target"
      echo "  ✅ Kopioitu: $relative"
    else
      echo "  ⏭️  Löytyy jo: $relative"
    fi
  else
    echo "  ⚠️  Projektia ei löydy: $target_dir (skipped)"
  fi
done

# --- Kopioi rclone config ---
echo "[2/4] Kopioidaan rclone/autostart-asetukset..."

if [ -f "$OLD_HOME/.config/rclone/rclone.conf" ]; then
  mkdir -p ~/.config/rclone
  cp "$OLD_HOME/.config/rclone/rclone.conf" ~/.config/rclone/
  echo "  ✅ rclone.conf kopioitu"
fi

if [ -d "$OLD_HOME/.config/autostart" ]; then
  mkdir -p ~/.config/autostart
  cp "$OLD_HOME/.config/autostart/"*.desktop ~/.config/autostart/ 2>/dev/null
  echo "  ✅ autostart-tiedostot kopioitu"
fi

# --- Python venv tälle projektille (Google AI) ---
echo "[3/4] Luodaan Python venv tälle projektille..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo "  ✅ venv luotu ja riippuvuudet asennettu"
else
  echo "  ⏭️  .venv löytyy jo"
fi

# --- Docker Compose ---
echo "[4/4] Käynnistetään Docker Compose..."

cd "$PROJECT_DIR"
if command -v docker &>/dev/null; then
  docker compose build
  docker compose up -d
  echo "  ✅ Docker-kontit käynnistetty"
  docker compose ps
else
  echo "  ⚠️  Docker ei ole vielä käytettävissä (logout+login tarvitaan)"
fi

echo ""
echo "=========================================="
echo "  ✅ Vaihe 4 valmis!"
echo "=========================================="
echo ""
echo "  Muista vielä:"
echo "  - az login        (Azure-kirjautuminen)"
echo "  - Luo muiden projektien venvit tarpeen mukaan"
echo ""
