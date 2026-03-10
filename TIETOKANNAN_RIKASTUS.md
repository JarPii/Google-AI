# Vektoritietokannan rikastussuunnitelma

## Tavoite

Rikastaa SearchAssistantin vektoritietokantaa kattamaan teollisen
pintakäsittelylaitoksen koko elinkaari: suunnittelu, rakentaminen,
prosessit, ohjaus, laadunhallinta, ympäristö ja talous.

## Nykytila

- **127 chunkia**, 16 lähdettä
- Pääosin sähkökemian perusteita (LibreTexts, Wikipedia)
- Turvallisuussäädöksiä (OSHA, ECHA, EPA)
- Kieli: pääosin englanti, 2 suomenkielistä lähdettä (korvataan englanninkielisillä)

## Tavoitetila

~400–500 chunkia, 8 aihealuetta katettuna.

## Kieliperiaate

> **Kaikki vektoritietokantaan talletettava data on englanniksi.**

Tämä koskee kaikkia chunkeja, lähdemateriaaleja ja metatietoja.
Perustelu:

- Embedding-malli (BAAI/bge-m3) toimii parhaiten yhtenäisellä kielellä
- Englanti on pintakäsittelyalan kansainvälinen tekninen kieli
- Vältetään sekakieliset hakutulokset ja epätasainen semanttinen haku
- Suomenkieliset lähteet korvataan englanninkielisillä vastineilla

**Monikielisyys toteutetaan erillisellä käännöskerroksella:**

```
Käyttäjä (fi/en/de/...) → Käännöskerros → LLM (englanniksi) → RAG-haku (en)
                                         → Vastaus käännetään käyttäjän kielelle
```

Käännöskerros lisätään myöhemmässä vaiheessa erillisenä komponenttina.

---

## 1. PROSESSIT (nykyistä syvemmälle)

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Sinkitys (kuuma-, sähkö-, mekaaninen) | Yleisin teollinen pinnoite | ❌ |
| Kromauskäsittelyt (kova-, koristekromaus) | Teollisuuden perusprosessi | ❌ |
| Nikkelöinti (Watts, sulfamaatti, kemiallinen) | Yleisimpiä galvaanisia prosesseja | ❌ |
| Kemiallinen nikkelöinti (electroless) | Tasainen pinnoite ilman virtaa | ❌ |
| Fosfatointi (Zn, Mn, Fe) | Esikäsittely, korroosioankkuri | ❌ |
| Maalauksen esikäsittely (zirkoni, silaani) | Moderni kromivapaa esikäsittely | ❌ |
| Kuumasinkitys (batch, jatkuva) | Suuria tonnimääriä teollisuudessa | ❌ |
| Peittaus ja puhdistus (happo, emäs, ultraääni) | Jokaisen linjaston perusoperaatio | ❌ |
| Huuhtelu (kaskadi, staattinen, ioninvaihto) | Kriittinen laatu + ympäristö | ❌ |

**Arvio: ~80–120 chunkia**

---

## 2. SÄHKÖTEKNIIKKA & AUTOMAATIO

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Tasasuuntaajat (SCR, IGBT, pulssivirta) | Virtalähteen valinta ja mitoitus | ❌ |
| Pulssivirtatekniikka (pulse, PPR) | Parantaa pinnoitelaatua | ❌ |
| Anodi–katodi-geometria | Heittokyvyn ja virranjakauman optimointi | ❌ |
| PLC-ohjaus pintakäsittelyssä | Prosessisekvenssit, kuljetinohjaus | ❌ |
| Prosessi-instrumentointi (pH, T, johtokyky, konsentraatio) | Kylpyjen hallinta | ❌ |
| SCADA ja valvomojärjestelmät | Koko laitoksen hallinta | ❌ |
| Sähköturvallisuus (märkätilat, EX-luokitukset) | Turvallisuuskriittinen ympäristö | ❌ |

**Arvio: ~30–50 chunkia**

---

## 3. LAITOS- JA LINJASUUNNITTELU

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Linjan layout-suunnittelu (barrel, rack, jatkuva) | Kapasiteetti, investointi | ❌ |
| Altaat ja materiaalit (PP, PE, PVDF, ruostumaton) | Kemiallinen kestävyys | ❌ |
| Kuljetinjärjestelmät (hoist, conveyor, barrel) | Automaatioaste, läpimenoaika | ❌ |
| Ilmanvaihto ja kohdepoisto | Kemiallisten höyryjen hallinta | ❌ |
| Lämmitys ja jäähdytys (immersiolämmittimet, lämmönvaihtimet) | Kylpylämpötilan hallinta | ❌ |
| Suodatus ja kylpynhoito (aktiivihiili, selkeytys) | Pinnoitteen laatu | ❌ |

**Arvio: ~30–40 chunkia**

---

## 4. KYLPYKEMIA & LAADUNHALLINTA

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Kylpyanalytiikka (Hull cell, titraus, AAS) | Kylpyjen kunnossapito | ❌ |
| Pinnoitteen testaus (paksuus, tartunta, kovuus, korroosiokoe) | Laadunvarmistus | ❌ |
| Vety-hauraustuminen | Kriittinen turvallisuusriski korkealujuusteräksille | ❌ |
| Kiilto- ja tasausaineet (brighteners, levelers) | Ulkonäkö ja tasaisuus | ❌ |
| Kylpyjen vianetsintä (troubleshooting) | Päivittäinen tuotanto-ongelma | ❌ |

**Arvio: ~30–40 chunkia**

---

## 5. YMPÄRISTÖ & JÄTEVEDENKÄSITTELY

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Jätevedenkäsittely (Cr(VI) pelkistys, CN hävitys, neutralointi) | Lakisääteinen velvoite | ❌ |
| Metallintalteenotto (ioninvaihto, elektrolyysi, RO) | Kiertotalous + kustannus | ❌ |
| BAT-päätelmät (pintakäsittely-BREF) | EU:n paras käytettävissä oleva tekniikka | ❌ |
| Ympäristöluvat ja päästörajat | Suomalainen lainsäädäntö | ❌ |
| Lietteen käsittely | Vaarallinen jäte, kustannus | ❌ |

**Arvio: ~40–60 chunkia**

---

## 6. STANDARDIT & SPESIFIKAATIOT

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| ISO 2081 (Zn-pinnoitteet), ISO 1456 (Ni+Cr) | Yleisimmät pinnoitestandardit | ❌ |
| SFS-EN ISO 12944 (maalaus, korroosioympäristöt C1–C5) | Teräsrakenteiden maalaus | ❌ |
| ASTM B117 (suolasumukoe) | Korroosiokestävyyden testaus | ❌ |
| AMS 2404/2405 (kova-/koristekromaus) | Ilmailuteollisuus | ❌ |
| RoHS, REACH, Cr(VI)-rajoitukset | Kemikaalilainsäädäntö | ❌ |

**Arvio: ~20–30 chunkia**

---

## 7. MATERIAALITIETOUS

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Teräkset ja pinnoitettavuus (hiiliteräs, ruostumaton, valurauta) | Esikäsittelyn valinta | ❌ |
| Alumiiniseokset ja anodisoinnin vaatimukset | Seoskohtaiset erot | ❌ |
| Muovien pinnoitus (ABS, PA, MID) | Kasvava ala | ❌ |
| Korroosiomekanismit (galvaaninen, piste-, rako-) | Miksi pinnoitetaan | ❌ |
| Sähkökemiallinen jännitesarja | Materiaalivalinnan perusta | ❌ |

**Arvio: ~20–30 chunkia**

---

## 8. TALOUS & TUOTANTO

| Aihealue | Miksi tärkeä | Tila |
|----------|-------------|------|
| Pinnoituskustannusten laskenta (€/dm², €/kg) | Tarjouslaskenta | ❌ |
| Energiankulutus (kWh per tonni/dm²) | Käyttökustannus | ❌ |
| Kapasiteettilaskenta (kpl/h, dm²/h) | Linjan mitoitus | ❌ |
| Kylpyjen käyttöikä ja kemikaalikustannukset | Budjetti | ❌ |

**Arvio: ~15–20 chunkia**

---

## Prioriteettijärjestys

| # | Aihealue | Chunkit (arvio) | Prioriteetti |
|---|----------|-----------------|-------------|
| 1 | Prosessit (Ni, Zn, Cr, kemiallinen Ni, peittaus, huuhtelu) | ~80–120 | 🔴 Korkein |
| 2 | Jätevedenkäsittely + ympäristö (BAT, Cr-pelkistys) | ~40–60 | 🔴 Korkein |
| 3 | Automaatio & instrumentointi (PLC, tasasuuntaajat) | ~30–50 | 🟡 Korkea |
| 4 | Kylpykemia & laadunhallinta (Hull cell, testit) | ~30–40 | 🟡 Korkea |
| 5 | Laitossuunnittelu (layout, altaat, kuljettimet) | ~30–40 | 🟡 Korkea |
| 6 | Standardit & spesifikaatiot | ~20–30 | 🟢 Normaali |
| 7 | Materiaalitietous & korroosiomekanismit | ~20–30 | 🟢 Normaali |
| 8 | Talous & kustannuslaskenta | ~15–20 | 🟢 Normaali |
| | **YHTEENSÄ** | **~265–390** | |

Yhdistettynä nykyiseen 127 chunkiin tavoite on **~400–500 chunkia**.

---

## Lähteiden valintakriteerit

- ✅ Avoin lisenssi (CC-BY, CC-BY-SA, public domain)
- ✅ Teknisesti luotettava (yliopistot, virastot, standardointielimet)
- ✅ **Vain englanti** (monikielisyys toteutetaan käännöskerroksella)
- ✅ Verkkopohjainen (scraping mahdollinen)
- ❌ Ei maksumuurin takana
- ❌ Ei tekijänoikeudella suojattua (kirjat, standardien kokotekstit)
- ❌ Ei suomen- tai muunkielisiä lähteitä tietokantaan
