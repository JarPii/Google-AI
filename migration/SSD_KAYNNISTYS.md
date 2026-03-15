# 💾 SSD suorakäynnistys (HP)

Näillä ohjeilla kone käynnistyy suoraan SSD:ltä ilman boot-valikkoa tai viiveitä.

## GRUB (käyttöjärjestelmätaso)

GRUB on jo konfiguroitu oikein — ei valikkoa, ei viivettä:

```
GRUB_DEFAULT=0
GRUB_TIMEOUT_STYLE=hidden
GRUB_TIMEOUT=0
```

Jos joskus pitää muuttaa, tiedosto on `/etc/default/grub` ja muutosten jälkeen:

```bash
sudo update-grub
```

## BIOS/UEFI (laitteistotaso)

Jos käynnistys silti pysähtyy tai näyttää vaihtoehtoja, se johtuu BIOSin asetuksista.

1. **Käynnistä kone uudelleen**
2. **Paina F10** heti kun HP-logo ilmestyy → BIOS Setup avautuu
3. **Siirry välilehdelle "Boot"** tai "Boot Options"
4. **Aseta boot-järjestys:**
   - 1. **Kingston SSD** (ainut aktiivinen)
   - Poista/disable: HDD, USB, verkko
5. **Fast Boot** → Enabled (jos löytyy)
6. **POST Delay** → 0 sekuntia (jos löytyy)
7. **Tallenna: F10 → Save & Exit**

## Hätätilanteessa

Jos tarvitset boot-valikon takaisin (esim. USB-tikku):

- **F9** käynnistyksen aikana → kertaluontoinen boot-valikko (ohittaa BIOS-asetukset)
- **F10** → BIOS Setup, lisää USB takaisin boot-järjestykseen

## Tarkistus

```bash
# Millä levyllä root on:
df / | tail -1

# Pitäisi näyttää /dev/sdb2 (SSD), ei /dev/sda (HDD)
```
