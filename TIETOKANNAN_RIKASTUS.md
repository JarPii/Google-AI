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

~450–550 chunkia, 9 aihealuetta katettuna:
- **public:** ~265–390 chunkia (julkiset lähteet)
- **proprietary:** ~46 chunkia (PLC-koodista generoitu dokumentaatio)
- **customer:** asiakaskohtainen data lisätään asiakasprojekteissa

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

## Tiedon luokittelu ja pääsynhallinta

> **Kaikella vektoritietokannan datalla on `access_level`-luokitus.**

Tietokannassa on kolmen tyyppistä dataa, jotka erotetaan metadata-sarakkeella:

```
┌───────────────────────────────────────────────────────────────┐
│  chunks-taulu                                                 │
│                                                               │
│  id │ content     │ embedding │ access_level │ customer_id    │
│  ───┼─────────────┼───────────┼──────────────┼───────────────│
│   1 │ "Faraday…"  │ [0.12,…]  │ public       │ NULL           │
│   2 │ "Our hoist…"│ [0.15,…]  │ proprietary  │ NULL           │
│   3 │ "Customer X │ [0.09,…]  │ customer     │ cust_123       │
│     │  bath 3…"   │           │              │                │
│   4 │ "Customer Y │ [0.11,…]  │ customer     │ cust_456       │
│     │  line 2…"   │           │              │                │
└───────────────────────────────────────────────────────────────┘
```

### Kolme tasoa

| Taso | `access_level` | `customer_id` | Sisältö | Esimerkki |
|------|---------------|---------------|---------|-----------|
| **public** | `public` | `NULL` | Julkiset lähteet, standardit, sähkökemian perusteet | Wikipedia, LibreTexts, OSHA |
| **proprietary** | `proprietary` | `NULL` | Oma yritystieto: PLC-kuvaukset, omat prosessiparametrit, sisäinen dokumentaatio | PLC-koodista generoidut toimintakuvaukset |
| **customer** | `customer` | `cust_XXX` | Asiakaskohtainen tieto: linjastokonfiguraatiot, kylpyreseptit, huoltohistoria | "Customer X line 2 Watts bath: NiSO₄ 280 g/L" |

### Kuka näkee mitä

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Ulkoinen / julkinen käyttö (ei kirjautumista)             │
│  → WHERE access_level = 'public'                           │
│  → Näkee vain julkisen tiedon                              │
│                                                            │
│  Sisäinen käyttäjä (oma yritys, kirjautunut)               │
│  → WHERE access_level IN ('public', 'proprietary')         │
│  → Näkee julkisen + yrityksen oman tiedon                  │
│  → EI näe asiakaskohtaista dataa (ellei valittu)           │
│                                                            │
│  Sisäinen käyttäjä + asiakaskonteksti                      │
│  → WHERE access_level IN ('public', 'proprietary')         │
│     OR (access_level = 'customer'                          │
│         AND customer_id = 'cust_123')                      │
│  → Näkee julkisen + oman + valitun asiakkaan tiedon        │
│                                                            │
│  Asiakas (oma portaali, tulevaisuudessa)                   │
│  → WHERE access_level = 'public'                           │
│     OR (access_level = 'customer'                          │
│         AND customer_id = 'cust_123')                      │
│  → Näkee julkisen + VAIN OMAN datansa                      │
│  → EI näe proprietary (yrityksen sisäinen)                 │
│  → EI näe muiden asiakkaiden dataa                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Tietokantalaajennus (toteutetaan kun data sitä vaatii)

```sql
ALTER TABLE chunks ADD COLUMN access_level TEXT NOT NULL DEFAULT 'public';
ALTER TABLE chunks ADD COLUMN customer_id  TEXT DEFAULT NULL;
ALTER TABLE chunks ADD COLUMN source_type  TEXT NOT NULL DEFAULT 'web';

-- source_type: 'web', 'plc', 'internal', 'csv', 'manual'
-- access_level: 'public', 'proprietary', 'customer'
-- customer_id: NULL (public/proprietary) tai asiakkaan tunniste

CREATE INDEX idx_chunks_access ON chunks(access_level);
CREATE INDEX idx_chunks_customer ON chunks(customer_id) WHERE customer_id IS NOT NULL;
```

### Turvallisuusperiaatteet

- ✅ Suodatus tapahtuu **SQL-tasolla ennen** vektorihaun tulosten palautusta
- ✅ Asiakasdata ei koskaan palaudu ilman oikeaa `customer_id`-suodatusta
- ✅ PLC-koodista tallennetaan vain generoitu kuvaus, ei lähdekoodia
- ✅ LLM:n system prompt ei sisällä asiakaskohtaista tietoa
- ✅ Sessioraportissa merkitään tiedon luokitus (public / proprietary / customer)
- ⚠️ Autentikointi (JWT/API-key → access_level + customer_id) toteutetaan myöhemmin

---

## 9. PLC-KOODISTA GENEROITU DOKUMENTAATIO

> Oma ohjausjärjestelmän PLC-koodi (IEC 61131-3 Structured Text)
> analysoidaan LLM:llä ja muutetaan englanninkielisiksi toimintakuvauksiksi.

### Lähtödata

39 ST-tiedostoa (OpenPLC-Simulator), pintakäsittelylinjan kuljettinohjaus:

| Moduuliryhmä | Tiedostoja | Kuvaus |
|---|---|---|
| `STC_FB_*` (Station Control) | 14 | Asemaohjaus, siirrot, aikataulutus, kalibrointi |
| `DEP_FB_*` (Departure) | 6 | Lähtöaikataulutus, slotit, overlap-laskenta |
| `TSK_FB_*` (Task) | 4 | Tehtävien analyysi, konfliktiratkaisu |
| `SIM_FB_*` (Simulation) | 4 | X/Z-liikesimulointi, konfiguraatio |
| `TWA_*` (Time Window) | 2 | Rajalaskenta, prioriteetti |
| `types.st, globals.st, config.st` | 3 | Datamallit, vakiot, asetukset |
| `plc_prg.st` | 1 | Pääohjelma |

### Generointiprosessi

```
PLC-koodi (.st)                     LLM analysoi
┌─────────────────┐                 ┌──────────────────────────────────┐
│ STC_FB_Main-    │                 │ "The Main Scheduler orchestrates │
│ Scheduler       │                 │  task and departure scheduling   │
│ - i_run, i_time │    ──────►      │  on alternating PLC scan cycles  │
│ - turn logic    │                 │  to prevent simultaneous         │
│ - TSK/DEP calls │                 │  execution..."                   │
└─────────────────┘                 └───────────────┬──────────────────┘
                                                    │
                                                    ▼
                                    Vektori-DB (access_level = 'proprietary')
```

### Generoidun kuvauksen rakenne (per tiedosto)

Jokaisesta FB:stä LLM generoi:

1. **MODULE NAME** — funktion nimi
2. **PURPOSE** — mitä moduuli tekee (1 kappale)
3. **INPUTS/OUTPUTS** — I/O-kuvaukset
4. **OPERATING LOGIC** — toimintalogiikka vaiheittain
5. **SAFETY** — lukitukset, virheenkäsittely
6. **INTEGRATION** — yhteydet muihin moduuleihin

### Chunkit PLC-koodista

| Chunkkityyppi | Määrä (arvio) | Esimerkki |
|---|---|---|
| FB-kohtainen toimintakuvaus | ~34 | "STC_FB_DispatchTask dispatches..." |
| Datamallit ja tyypit | ~6 | "STATION_T describes a station..." |
| Arkkitehtuurikuva | ~2 | "The system consists of three scheduler layers..." |
| Sekvenssikaaviot (tekstinä) | ~4 | "Normal cycle: TSK_TURN → DEP_TURN → TSK_TURN..." |
| **YHTEENSÄ** | **~46** | |

### Turvallisuus

- ✅ Vain generoitu englanninkielinen kuvaus tallennetaan, **EI lähdekoodia**
- ✅ `access_level = 'proprietary'` — ei näy ulkoisille käyttäjille
- ✅ Asiakasnimet ja spesifit parametrit anonymisoidaan kuvauksissa
- ✅ Generoitu kuvaus tarkistetaan ennen tallennusta

### Toteutustyökalu

```
scripts/plc_to_docs.py
  → Lukee .st-tiedostot
  → Lähettää LLM:lle (Azure OpenAI) analysoitavaksi
  → Tallentaa generoidut kuvaukset chunks-tauluun
  → access_level = 'proprietary', source_type = 'plc'
```

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
| 9 | PLC-koodista generoitu dokumentaatio (proprietary) | ~46 | 🟡 Korkea |
| | **YHTEENSÄ** | **~311–436** | |

Yhdistettynä nykyiseen 127 chunkiin tavoite on **~450–550 chunkia**.

---

## Lähteiden valintakriteerit

- ✅ Avoin lisenssi (CC-BY, CC-BY-SA, public domain)
- ✅ Teknisesti luotettava (yliopistot, virastot, standardointielimet)
- ✅ **Vain englanti** (monikielisyys toteutetaan käännöskerroksella)
- ✅ Verkkopohjainen (scraping mahdollinen)
- ❌ Ei maksumuurin takana
- ❌ Ei tekijänoikeudella suojattua (kirjat, standardien kokotekstit)
- ❌ Ei suomen- tai muunkielisiä lähteitä tietokantaan

### Sisäisten lähteiden kriteerit (proprietary / customer)

- ✅ PLC-koodista generoitu kuvaus (ei lähdekoodi)
- ✅ Anonymisoitu (ei asiakasnimiä kuvauksissa)
- ✅ `access_level` ja `customer_id` asetettu oikein
- ✅ Generoitu sisältö tarkistettu ennen tallennusta
- ❌ Ei raakaa lähdekoodia vektoritietokantaan
- ❌ Asiakasdata ei saa näkyä muille asiakkaille
