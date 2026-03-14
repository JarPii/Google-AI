#!/bin/bash
# =============================================================================
# Vaihe 3: HDD mounttaus data-levyksi
# Mounttaa vanhan HDD:n /mnt/hdd:ksi, luo symlinkit
# =============================================================================
set -e

echo "=========================================="
echo "  Vaihe 3: HDD mounttaus"
echo "=========================================="

HDD_DEVICE="/dev/sda4"
MOUNT_POINT="/mnt/hdd"

# --- Tarkista että HDD löytyy ---
echo "[1/4] Tarkistetaan HDD..."
if ! lsblk "$HDD_DEVICE" &>/dev/null; then
  echo "  ❌ $HDD_DEVICE ei löydy! Tarkista lsblk -tuloste:"
  lsblk -o NAME,SIZE,TYPE,FSTYPE,MODEL
  exit 1
fi
echo "  ✅ $HDD_DEVICE löytyi"

# --- Luo mount-piste ---
echo "[2/4] Luodaan mount-piste $MOUNT_POINT..."
sudo mkdir -p "$MOUNT_POINT"

# --- Lisää fstabiin ---
echo "[3/4] Konfiguroidaan automaattinen mount..."
UUID=$(sudo blkid -s UUID -o value "$HDD_DEVICE")
echo "  HDD UUID: $UUID"

if grep -q "$UUID" /etc/fstab; then
  echo "  ⏭️  Löytyy jo fstabista"
else
  echo "# Vanha HDD data-levynä" | sudo tee -a /etc/fstab
  echo "UUID=$UUID  $MOUNT_POINT  ext4  defaults,noatime  0  2" | sudo tee -a /etc/fstab
  echo "  ✅ Lisätty fstabiin"
fi

# --- Mount ---
sudo mount -a
echo "  ✅ Mountattu: $(df -h $MOUNT_POINT | tail -1)"

# --- Symlinkit ---
echo "[4/4] Luodaan symlinkit..."

# Downloads → HDD (Takeout-zipit yms. isot tiedostot)
if [ -d "$MOUNT_POINT/home/jarpii/Downloads" ]; then
  # Poista tyhjä Downloads jos on
  rmdir ~/Downloads 2>/dev/null || true
  if [ ! -L ~/Downloads ]; then
    ln -s "$MOUNT_POINT/home/jarpii/Downloads" ~/Downloads
    echo "  ✅ ~/Downloads → HDD"
  else
    echo "  ⏭️  ~/Downloads linkki on jo"
  fi
fi

echo ""
echo "=========================================="
echo "  ✅ Vaihe 3 valmis!"
echo "=========================================="
echo ""
echo "  HDD mountattu: $MOUNT_POINT"
echo "  Vanha home: $MOUNT_POINT/home/jarpii/"
echo ""
