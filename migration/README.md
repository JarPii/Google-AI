# 🔄 OS-migraatio: HDD → SSD

## Lähtötilanne
- **Vanha**: Ubuntu 24.04 HDD:llä (WD 500GB, 101 MB/s)
- **Uusi**: Puhdas Ubuntu 24.04 SSD:lle (Kingston 240GB, 277 MB/s)
- **HDD jää data-levyksi** (Downloads, Takeout-backupit)

## Toimintasuunnitelma

### Ennen asennusta (vanha järjestelmä)
1. Varmista että kaikki Git-repot on commitattu ja pushattu
2. Tarkista `.env`-tiedostot — ne EIVÄT ole Gitissä!
3. Kopioi tärkeät asetukset talteen (rclone, autostart)

### Asennusjärjestys

| Vaihe | Mitä | Miten | Skripti |
|-------|------|-------|---------|
| **0** | Asenna Ubuntu 24.04 SSD:lle | Manuaalisesti USB:ltä | - |
| **1** | Asenna VS Code | `sudo snap install code --classic` | - |
| **2** | Kloonaa tämä projekti | `git clone https://github.com/JarPii/Google-AI.git` | - |
| **3** | Perusohjelmat | Agentti ajaa | `01_system_packages.sh` |
| **4** | Dev-työkalut & snap | Agentti ajaa | `02_dev_tools.sh` |
| **5** | HDD mounttaus | Agentti ajaa | `03_mount_hdd.sh` |
| **6** | Projektien palautus | Agentti ajaa | `04_restore_projects.sh` |
| **7** | Tarkistus | Agentti ajaa | `05_verify.sh` |

### Manuaaliset vaiheet (0-2)

```bash
# Vaihe 0: Ubuntu-asennus
# - Boottaa USB:ltä (F9 HP:ssä)
# - "Something else" → osiointi:
#   /dev/sdb1 = 512 MB EFI
#   /dev/sdb2 = 223 GB ext4, mountpoint /
#   Boot loader → /dev/sdb
# - Käyttäjänimi: jarpii

# Vaihe 1: Ensimmäisen bootin jälkeen, avaa terminaali:
sudo snap install code --classic

# Vaihe 2: Kloonaa tämä projekti
mkdir -p ~/Dev
cd ~/Dev
git clone https://github.com/JarPii/Google-AI.git "Google AI"

# Vaihe 3: Avaa VS Code ja pyydä agenttia:
# "Aja migration-skriptit järjestyksessä"
code ~/Dev/"Google AI"
```

## Tiedostot

```
migration/
├── README.md                  ← Tämä ohje
├── 01_system_packages.sh      ← APT-paketit, Docker, Node, Chrome, Azure CLI
├── 02_dev_tools.sh            ← Snap-ohjelmat, VS Code extensionit, Git config
├── 03_mount_hdd.sh            ← HDD → /mnt/hdd, fstab, symlinkit
├── 04_restore_projects.sh     ← .env kopiointi, venv-luonti, Docker-kontit
├── 05_verify.sh               ← Tarkistaa kaiken toimivuuden
└── dotfiles/                  ← Varmuuskopio asetuksista
    ├── gitconfig
    ├── rclone.conf
    └── autostart/
```

## Muistiinpanot

### Asiat jotka EIVÄT siirry automaattisesti
- Chrome-kirjanmerkit → synkkaa Google-tilillä automaattisesti
- Azure login → `az login` uudelleen
- SSH-avaimet → luo uudet tarvittaessa
- Docker-volumet (PostgreSQL-data) → rebuild `docker compose up`
- pCloud/rclone-tunnukset → kirjaudu uudelleen

### Arvioitu kokonaisaika
- Ubuntu-asennus: ~30 min
- Skriptit: ~30 min (agentti ajaa)
- Venvien luonti: ~15 min
- Docker build: ~15 min
- **Yhteensä: ~1.5 h**
