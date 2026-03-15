# 🔑 Salasanan vaihto USB-tikulta

Jos et pääse kirjautumaan SSD:ltä käynnistyvään Ubuntuun, voit vaihtaa salasanan Ubuntu-asennustikulta.

## Ohjeet

1. **Sammuta kone**
2. **Työnnä USB-tikku kiinni** (sama jolla asensit Ubuntun)
3. **Käynnistä ja paina F9** → valitse USB-tikku
4. **Valitse "Try Ubuntu"** (älä "Install")
5. **Avaa terminaali** (Ctrl+Alt+T)
6. **Tarkista levyjen nimet:**
   ```bash
   lsblk
   ```
   Etsi SSD:n suurin ext4-osio (noin 223 GB), esim. `/dev/sdb2`

7. **Mounttaa SSD ja vaihda salasana:**
   ```bash
   sudo mount /dev/sdb2 /mnt
   sudo chroot /mnt
   passwd jarpii
   ```
   Kirjoita uusi salasana kahdesti kun kysyy.

8. **Sulje ja käynnistä uudelleen:**
   ```bash
   exit
   sudo umount /mnt
   reboot
   ```

9. **Irrota USB-tikku** kun kone käynnistyy uudelleen

## Miksi salasana "muuttui"?

Todennäköisin syy on näppäimistöasettelun vaihtuminen. Migraatioskripti `01_system_packages.sh` asentaa suomen kielipaketin (`language-pack-fi`), mikä voi vaihtaa näppäimistöasettelun. Tällöin erikoismerkit (esim. `@`, `!`, `#`) kirjoittuvat eri tavalla kuin asennusvaiheessa.

Kirjautumisen jälkeen tarkista näppäimistöasettelu: **Asetukset → Alue ja kieli → Syöttölähteet**.
