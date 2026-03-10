# Calc-moduulin rikastussuunnitelma

## Kieliperiaate

> **Kaikki calc-moduulin koodi, docstringit, muuttujanimet, LaTeX-selitykset
> ja palautusarvot ovat englanniksi.**

- Funktioiden nimet, parametrit ja docstringit englanniksi
- `calculation_steps` (LaTeX) englanniksi
- Materiaalitaulukoiden avaimet ja kuvaukset englanniksi
- Kommentit koodissa englanniksi

**Monikielisyys toteutetaan erillisellä käännöskerroksella**, joka kääntää
LLM:n vastauksen (sisältäen calc-tulokset) käyttäjän kielelle.
Calc-moduuli itse ei sisällä lokalisointia.

---

## Periaate: calc vs. vektoritietokanta

Jokainen aihealue sisältää sekä **laskennallista** (calc) että **tiedollista**
(vektoritietokanta) ulottuvuutta. Jako noudattaa selkeää sääntöä:

| | Calc-moduuli | Vektoritietokanta |
|---|---|---|
| **Rooli** | Deterministinen laskenta | Kontekstitieto ja selitykset |
| **Vastaa kysymykseen** | *"Paljonko?"* | *"Miksi, milloin, miten?"* |
| **Esimerkki** | `faraday_mass(10, 3600, 63.55, 2)` → `1.186 g` | "Copper plating typically uses 2–5 A/dm²" |
| **Tarkkuus** | Eksakti, matemaattinen | Heuristinen, kokemuspohjainen |
| **Toteutus** | Python-funktio + LaTeX | Teksti chunkeina pgvector-haussa |

### Mittayksiköt – sekä-että -esimerkki

```
┌──────────────────────────────────────────────────────┐
│  Käyttäjä: "Muunna 5 A/dm² yksiköön A/m²"           │
│                                                      │
│  1. Vektoritietokanta kertoo LLM:lle:               │
│     "1 dm² = 0.01 m², joten A/dm² → A/m²            │
│      kerroin on ×100. A/dm² on pintakäsittelyn       │
│      vakioyksikkö."                                  │
│                                                      │
│  2. Calc-funktio laskee:                             │
│     unit_conversion(5, "desi", "perus", "A/m²")     │
│     → MUTTA: tämä on neliöyksikkö, joten tarvitaan  │
│       erillinen area_unit_conversion()               │
│                                                      │
│  3. Tai: domain_unit_conversion("current_density",   │
│          5, "A/dm²", "A/m²") → 500 A/m²             │
└──────────────────────────────────────────────────────┘
```

---

## Nykytila

| Funktio | Tiedosto | Kuvaus |
|---------|----------|--------|
| `faraday_mass_calculation` | `surface_treatment.py` | Faradayn laki: massa |
| `faraday_thickness_calculation` | `surface_treatment.py` | Paksuus massasta |
| `current_density_calculation` | `surface_treatment.py` | Virtatiheys I/A |
| `unit_conversion` | `surface_treatment.py` | SI-etuliitemuunnos |

---

## Uudet funktiot aihealueittain

### 1. SÄHKÖKEMIA & PROSESSIT

| Funktio | Kaava | Syötteet | Tulos | Prioriteetti |
|---------|-------|----------|-------|-------------|
| `ohms_law_electrolyte` | $V = I \cdot R$ + ylijännitteet | I, R_liuos, η_anodi, η_katodi | V (V) | 🔴 |
| `nernst_equation` | $E = E^0 - \frac{RT}{zF}\ln Q$ | E0, T, z, Q | E (V) | 🔴 |
| `energy_consumption` | $W = V \cdot I \cdot t$ | V, I, t | kWh | 🔴 |
| `specific_energy` | $w = \frac{V \cdot I \cdot t}{m}$ | V, I, t, m | kWh/kg | 🟡 |
| `coulombic_efficiency` | $\eta = \frac{m_{todellinen}}{m_{teoreettinen}} \times 100$ | m_actual, m_theoretical | % | 🔴 |
| `throwing_power_haring` | Haring–Blum: $TP = \frac{K-M}{K+M-2} \times 100$ | K (etäisyyssuhde), M (massasuhde) | % | 🟡 |
| `wagner_number` | $Wa = \frac{\kappa}{i_0} \cdot \frac{\partial \eta}{\partial i}$ | κ, i₀, dη/di, L | dimensioton | 🟡 |

**Tiedosto:** `calc/electrochemistry.py`

### 2. PINNOITTEEN MITOITUS

| Funktio | Kaava | Syötteet | Tulos | Prioriteetti |
|---------|-------|----------|-------|-------------|
| `plating_time` | $t = \frac{d \cdot \rho \cdot A \cdot z \cdot F}{I \cdot M}$ | d(µm), ρ, A, z, I, M | t (s, min) | 🔴 |
| `required_current` | $I = \frac{d \cdot \rho \cdot A \cdot z \cdot F}{t \cdot M}$ | d(µm), ρ, A, z, t, M | I (A) | 🔴 |
| `coating_weight` | $m = d \cdot \rho \cdot A$ | d(µm), ρ(g/cm³), A(dm²) | m (g) | 🟡 |
| `corrosion_rate_mpy` | $CR = \frac{534 \cdot W}{D \cdot A \cdot t}$ | W(mg), D(g/cm³), A(in²), t(h) | mpy | 🟡 |
| `salt_spray_hours` | Taulukkolookup ISO 9227 | pinnoite, paksuus, standardi | h | 🟢 |

**Tiedosto:** `calc/coating.py`

### 3. KYLPYMITOITUS & KEMIA

| Funktio | Kaava | Syötteet | Tulos | Prioriteetti |
|---------|-------|----------|-------|-------------|
| `tank_volume` | $V = L \times W \times H$ | L, W, H (m) | litraa | 🔴 |
| `chemical_addition` | $m = V \cdot (c_{tavoite} - c_{nykyinen})$ | V(L), c_target, c_current | g tai mL | 🔴 |
| `ph_calculation` | $pH = -\log_{10}[H^+]$ | [H+] tai vahva happo/emäs | pH | 🟡 |
| `ph_adjustment` | Puskurikapasiteetti + tilavuus | V, pH_nyt, pH_tavoite, puskuri | mL happoa/emästä | 🟡 |
| `hull_cell_current_range` | $J(x) = I \cdot (51.47 - 52.42 \cdot \log x)$ | I(A), x(cm) | J(A/dm²) vs. x | 🔴 |
| `conductivity_to_resistivity` | $\rho = \frac{1}{\kappa}$ | κ (mS/cm) | ρ (Ω·cm) | 🟢 |
| `metal_concentration_from_density` | Empiiriset korrelaatiot | tiheys (g/L), kylpytyyppi | g/L metallia | 🟡 |

**Tiedosto:** `calc/bath_chemistry.py`

### 4. HUUHTELU & VEDENKÄSITTELY

| Funktio | Kaava | Syötteet | Tulos | Prioriteetti |
|---------|-------|----------|-------|-------------|
| `rinse_ratio` | $R = \frac{C_{kylpy}}{C_{max,huuhtelu}}$ | C_bath, C_max | R (dimensioton) | 🔴 |
| `cascade_rinse_stages` | $n = \frac{\log R}{\log r_{yksittäinen}}$ | R, r_per_stage | n (vaiheluku) | 🔴 |
| `rinse_water_flow` | $Q = \frac{V_{ulosveto} \cdot C_{kylpy}}{C_{max}}$ | V_dragout, C_bath, C_max | L/h | 🔴 |
| `dragout_volume` | $V = k \cdot A$ | k(mL/dm²), A(dm²) | mL | 🟡 |
| `wastewater_neutralization` | $m_{NaOH} = \frac{V \cdot c_{H^+} \cdot M_{NaOH}}{1000}$ | V, c_happo, M | g NaOH | 🟡 |
| `chromate_reduction_dose` | $3NaHSO_3 + 2CrO_4^{2-} ...$ stoikiometria | V, c_Cr6+ | g NaHSO₃ | 🟡 |
| `cyanide_destruction_dose` | $NaOCl + CN^- ...$ stoikiometria | V, c_CN | g NaOCl | 🟡 |
| `metal_hydroxide_precipitation_ph` | Liukoisuustulon perusteella | metalli, c_metalli | pH_min | 🟢 |

**Tiedosto:** `calc/rinse_wastewater.py`

### 5. SÄHKÖTEKNIIKKA & ENERGÍA

| Funktio | Kaava | Syötteet | Tulos | Prioriteetti |
|---------|-------|----------|-------|-------------|
| `rectifier_sizing` | $P = V_{max} \cdot I_{max} \cdot 1.2$ | V, I, varakerroin | kW, kVA | 🔴 |
| `bus_bar_voltage_drop` | $\Delta V = \frac{\rho \cdot L \cdot I}{A}$ | ρ_Cu, L, I, A | V | 🟡 |
| `anode_area_ratio` | $\frac{A_a}{A_c}$ suositus | A_katodi, suhde | A_anodi (dm²) | 🟡 |
| `heating_time` | $t = \frac{m \cdot c_p \cdot \Delta T}{P}$ | V(L), ΔT, P(kW) | t (min) | 🟡 |
| `heat_loss_tank` | $Q = U \cdot A \cdot \Delta T$ | U, A_pinta, ΔT | W | 🟢 |
| `exhaust_airflow` | $Q = v \cdot A_{aukko}$ | v(m/s), A(m²) | m³/s | 🟢 |

**Tiedosto:** `calc/electrical.py`

### 6. TALOUS & TUOTANTO

| Funktio | Kaava | Syötteet | Tulos | Prioriteetti |
|---------|-------|----------|-------|-------------|
| `plating_cost_per_area` | $C = C_{sähkö} + C_{kemikaalit} + C_{työ}$ | kWh-hinta, kemikaali-€, dm² | €/dm² | 🔴 |
| `line_capacity` | $n = \frac{t_{käytettävissä}}{t_{sykli}}$ | t_available, t_cycle | kpl/h | 🟡 |
| `chemical_cost_per_kg_deposit` | $C = \frac{c_{kemikaali} \cdot kulutus}{tuotto}$ | hinta/kg, kulutus, CE% | €/kg | 🟡 |
| `electricity_cost` | $C = \frac{V \cdot I \cdot t}{1000} \cdot hinta_{kWh}$ | V, I, t, €/kWh | € | 🟡 |
| `payback_period` | $t = \frac{investointi}{säästö/vuosi}$ | €_invest, €_savings/a | vuosia | 🟢 |

**Tiedosto:** `calc/economics.py`

### 7. MITTAYKSIKÖT & MUUNNOKSET (laajennus)

Yksikkömuunnoksissa on **kolme eri tasoa**:

```
Taso 1: SI-etuliitemuunnos     milli → kilo         (nykyinen unit_conversion)
Taso 2: Domain-yksikkömuunnos  dm² → ft², µm → mil  (saman suureen eri yksiköt)
Taso 3: Suureiden välinen      J = W × s, Ah = A × h (eri suureiden yhteys)
```

#### Taso 1: SI-etuliitemuunnos (nykyinen)

Toteutettu: `unit_conversion()` — piko → giga, lineaarinen skaalaus.

#### Taso 2: Domain-yksikkömuunnos (saman suureen eri yksiköt)

| Funktio | Kuvaus | Syötteet | Prioriteetti |
|---------|--------|----------|-------------|
| `area_unit_conversion` | dm² ↔ cm² ↔ m² ↔ ft² ↔ in² | arvo, yksiköstä, yksikköön | 🔴 |
| `thickness_unit_conversion` | µm ↔ mil ↔ mm ↔ in | arvo, yksiköstä, yksikköön | 🔴 |
| `concentration_conversion` | g/L ↔ oz/gal ↔ mol/L ↔ ppm | arvo, yksiköstä, yksikköön | 🟡 |
| `temperature_conversion` | °C ↔ °F ↔ K | arvo, yksiköstä, yksikköön | 🟡 |
| `current_density_conversion` | A/dm² ↔ A/ft² ↔ A/m² ↔ ASF | arvo, yksiköstä, yksikköön | 🔴 |
| `volume_conversion` | L ↔ gal(US) ↔ gal(UK) ↔ m³ | arvo, yksiköstä, yksikköön | 🟡 |
| `flow_rate_conversion` | L/h ↔ L/min ↔ gpm ↔ m³/h | arvo, yksiköstä, yksikköön | 🟢 |
| `mass_conversion` | g ↔ kg ↔ lb ↔ oz(troy) | arvo, yksiköstä, yksikköön | 🟢 |
| `pressure_conversion` | Pa ↔ bar ↔ atm ↔ psi | arvo, yksiköstä, yksikköön | 🟢 |

#### Taso 3: Suureiden väliset muunnokset (fysikaaliset yhteydet)

Nämä eivät ole pelkkiä kertoimia vaan **fysiikan lakeihin perustuvia
yhtälöitä** — eri suureiden välisiä riippuvuuksia:

| Funktio | Yhteys | Kaava | Syötteet | Prioriteetti |
|---------|--------|-------|----------|-------------|
| `energy_conversion` | J ↔ Wh ↔ kWh ↔ cal ↔ eV ↔ kJ | $1\text{ J} = 1\text{ W} \cdot \text{s}$, $1\text{ kWh} = 3.6\text{ MJ}$ | arvo, yksiköstä, yksikköön | 🔴 |
| `power_from_energy` | $P = \frac{E}{t}$ | W = J / s | E(J), t(s) | 🔴 |
| `energy_from_power` | $E = P \cdot t$ | J = W × s, kWh = kW × h | P, t, yksikkö | 🔴 |
| `charge_from_current` | $Q = I \cdot t$ | C = A × s, Ah = A × h | I(A), t(s tai h) | 🔴 |
| `current_from_charge` | $I = \frac{Q}{t}$ | A = C / s | Q(C tai Ah), t | 🟡 |
| `voltage_from_power` | $V = \frac{P}{I}$ | V = W / A | P(W), I(A) | 🟡 |
| `resistance_from_resistivity` | $R = \frac{\rho \cdot L}{A}$ | Ω = Ω·m × m / m² | ρ, L, A | 🟡 |
| `conductance_from_resistance` | $G = \frac{1}{R}$, $\kappa = \frac{1}{\rho}$ | S = 1/Ω, S/m = 1/(Ω·m) | R tai ρ | 🟢 |
| `force_from_pressure` | $F = p \cdot A$ | N = Pa × m² | p(Pa), A(m²) | 🟢 |
| `density_mass_volume` | $\rho = \frac{m}{V}$, $m = \rho \cdot V$, $V = \frac{m}{\rho}$ | tunnetut 2/3 → tuntematon | m, V, ρ (2/3) | 🟡 |

##### Pintakäsittelyssä yleisimmät suureyhteydet

| Tilanne | Muunnostarve | Esimerkki |
|---------|-------------|-----------|
| Energiankulutus | kWh ← V × A × h | "12 V, 500 A, 2 h → 12 kWh" |
| Sähkövaraus | Ah ← A × h, C ← A × s | "500 A × 3600 s = 1 800 000 C" |
| Faradayn laki | g ← C × M / (z × F) | "varaus → massa" (nykyinen) |
| Tasasuuntaaja | kW ← V × A | "12 V × 3000 A = 36 kW" |
| Lämmitys | kJ ← kg × c_p × ΔT | "500 L vettä 20→60 °C" |
| Johdin | V_drop ← Ω·m × m × A / m² | "johtokiskon häviö" |

**Tiedosto:** `calc/unit_conversions.py` (kaikki 3 tasoa samassa tiedostossa,
nykyinen SI-muunnos siirretään tänne tai kutsutaan täältä)

### Mittayksiköt: calc vs. vektoritietokanta

| Näkökulma | Calc | Vektoritietokanta |
|-----------|------|-------------------|
| Muuntokertoimet | ✅ `dm²_to_m2(5)` → `0.05` | ❌ |
| Suureyhteys J = W × s | ✅ `energy_from_power(36000, 3600)` → `36 kWh` | ❌ |
| "Mikä on alan vakioyksikkö?" | ❌ | ✅ "A/dm² is the industry standard" |
| Virtatiheyden muunto | ✅ `5 A/dm² → 500 A/m²` | ❌ |
| "Miksi A/dm² eikä A/m²?" | ❌ | ✅ "Historical convention, practical magnitude" |
| Lämpötilamuunnos °C↔°F | ✅ `celsius_to_f(65)` → `149°F` | ❌ |
| "Kylvyn lämpötila 60–70 °C" | ❌ | ✅ Process parameter knowledge |
| Suureiden yhteys sanallisesti | ❌ | ✅ "Power = Voltage × Current, 1 kWh = 3.6 MJ" |

**Yhteenveto:**
- **Calc** laskee eksaktin muunnoksen (numeerinen tulos + LaTeX)
- **Vektoritietokanta** selittää suureiden väliset yhteydet sanallisesti ja
  kertoo mitkä yksiköt ovat alan käytäntö missäkin kontekstissa

---

## Tiedostorakenne (tavoite)

```
calc/
├── __init__.py              ← exportoi kaikki funktiot
├── surface_treatment.py     ← nykyiset (Faraday, virtatiheys)
├── electrochemistry.py      ← Nernst, Ohm, tehokkuus
├── coating.py               ← pinnoitemitoitus, korroosio
├── bath_chemistry.py        ← kylpylaskenta, Hull cell, pH
├── rinse_wastewater.py      ← huuhtelu, jätevesi, stoikiometria
├── electrical.py            ← tasasuuntaajat, johdot, lämmitys
├── economics.py             ← kustannus, kapasiteetti, takaisinmaksu
├── unit_conversions.py      ← 3 tasoa: SI-etuliite, domain, suureyhteys
└── material_data.py         ← materiaalitaulukot (tiheys, M, z, E0)
```

### `material_data.py` – vakiotaulukot

Tämä ei ole laskentafunktio vaan **lookup-data**, jota muut funktiot
ja LLM voivat hyödyntää:

```python
METALS = {
    "Cu":  {"M": 63.546, "z": 2, "rho": 8.96,  "E0": +0.34},
    "Ni":  {"M": 58.693, "z": 2, "rho": 8.90,  "E0": -0.257},
    "Zn":  {"M": 65.38,  "z": 2, "rho": 7.13,  "E0": -0.763},
    "Cr":  {"M": 51.996, "z": 6, "rho": 7.19,  "E0": -0.744},
    "Sn":  {"M": 118.71, "z": 2, "rho": 7.29,  "E0": -0.138},
    "Au":  {"M": 196.97, "z": 3, "rho": 19.30, "E0": +1.498},
    "Ag":  {"M": 107.87, "z": 1, "rho": 10.49, "E0": +0.799},
    "Cd":  {"M": 112.41, "z": 2, "rho": 8.65,  "E0": -0.403},
    "Pb":  {"M": 207.2,  "z": 2, "rho": 11.34, "E0": -0.126},
    "Fe":  {"M": 55.845, "z": 2, "rho": 7.87,  "E0": -0.447},
}
```

LLM voi kutsua esim. `faraday_mass_calculation` ilman, että käyttäjän
tarvitsee tietää kuparin moolimassaa – LLM hakee sen taulukosta.

---

## Toteutusjärjestys

| Vaihe | Tiedosto | Funktiot | Arvioitu työ |
|-------|----------|----------|-------------|
| **1** | `material_data.py` | METALS-taulukko | 0.5 h |
| **2** | `unit_conversions.py` | 9 domain-muunnosta (taso 2) + 10 suureyhtälöä (taso 3) | 4 h |
| **3** | `electrochemistry.py` | 7 funktiota (Nernst, Ohm, CE%, Wagner) | 3 h |
| **4** | `coating.py` | 5 funktiota (pinnoitusaika, paksuus, korroosio) | 2 h |
| **5** | `bath_chemistry.py` | 7 funktiota (Hull cell, pH, kemikaali) | 3 h |
| **6** | `rinse_wastewater.py` | 8 funktiota (huuhtelu, neutralointi) | 3 h |
| **7** | `electrical.py` | 6 funktiota (tasasuuntaaja, lämmitys) | 2 h |
| **8** | `economics.py` | 5 funktiota (kustannus, kapasiteetti) | 2 h |
| **9** | Integrointi `rag_api.py` | TOOLS + TOOL_DISPATCH päivitys | 3 h |
| | **YHTEENSÄ** | **~64 funktiota** | **~22.5 h** |

---

## Integraatiomuistilista

Jokaisen uuden funktion kohdalla:

1. ✅ Funktio palauttaa `dict` jossa numeerinen tulos + `calculation_steps` (LaTeX **englanniksi**)
2. ✅ Docstring **englanniksi** – kuvaa argumentit, yksikkövaatimukset ja esimerkin
3. ✅ Rekisteröidään `TOOLS`-listaan (`rag_api.py`)
4. ✅ Lisätään `TOOL_DISPATCH`-dictionaryyn
5. ✅ Testataan yksikkötestillä (`api/test_math.py` tai uusi `tests/`)
6. ✅ Testataan LLM:n kautta (luonnollisella kielellä)

---

## Yhteys vektoritietokannan rikastukseen

Katso [TIETOKANNAN_RIKASTUS.md](TIETOKANNAN_RIKASTUS.md) – calc-moduulin
ja vektoritietokannan rikastus täydentävät toisiaan:

| Aihe | Calc antaa | Vektori-DB antaa |
|------|-----------|-----------------|
| Nickel plating | `faraday_mass(I, t, 58.69, 2)` | "Watts bath composition: NiSO₄ 250 g/L..." |
| Rinsing | `cascade_rinse_stages(10000, 30)` | "Three-stage counter-current rinsing reduces water usage by 97%..." |
| Cost | `plating_cost_per_area(...)` | "Decorative chrome plating typical market price 15–30 €/dm²..." |
| Rectifier | `rectifier_sizing(12, 3000)` | "IGBT rectifier advantages: better efficiency, pulse plating..." |
