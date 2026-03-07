"""
Pintakäsittelyn ja sähkökemian laskentakaavat.
Nämä funktiot on suunniteltu sekä ohjelmalliseen käyttöön että kielimallien
tehtäväkutsujen (function calling / tools) taustalle. Kaikki funktiot
palauttavat selkokielisen LaTeX-muotoillun selityksen käyttöliittymää varten.
"""

FARADAY_CONSTANT = 96485.3321  # C/mol (As/mol)

def faraday_mass_calculation(current_a: float, time_s: float, molar_mass: float, electrons: int) -> dict:
    """
    Laskee saostuneen aineen massan Faradayn elektrolyysilain avulla.
    
    Kaava: m = (I * t * M) / (z * F)
    
    Argumentit:
    - current_a (float): Sähkövirta ampeereina (A)
    - time_s (float): Aika sekunteina (s)
    - molar_mass (float): Aineen moolimassa (g/mol), esim. Cu = 63.546 g/mol
    - electrons (int): Siirtyvien elektronien hapetusluku / lukumäärä (z), esim. Cu2+ = 2
    
    Palauttaa:
    - dict: Sisältää:
        'mass_g' (float): Saostunut massa grammoina
        'calculation_steps' (str): Laskukaava ja vaiheet LaTeX-muodossa
    """
    mass = (current_a * time_s * molar_mass) / (electrons * FARADAY_CONSTANT)
    
    latex_string = (
        f"Lasketaan massa Faradayn lailla:\n"
        f"$$ m = \\frac{{I \\cdot t \\cdot M}}{{z \\cdot F}} $$\n\n"
        f"Sijoitetaan arvot:\n"
        f"$$ m = \\frac{{{current_a}\\text{{ A}} \\cdot {time_s}\\text{{ s}} \\cdot {molar_mass}\\text{{ g/mol}}}}{{{electrons} \\cdot {FARADAY_CONSTANT:.0f}\\text{{ C/mol}}}} $$\n\n"
        f"Tulos:\n"
        f"$$ m \\approx {mass:.4f} \\text{{ g}} $$"
    )
    
    return {
        "mass_g": mass,
        "calculation_steps": latex_string
    }

def faraday_thickness_calculation(mass_g: float, density_g_cm3: float, area_dm2: float) -> dict:
    """
    Laskee pinnoitteen paksuuden massan, tiheyden ja pinta-alan perusteella.
    
    Argumentit:
    - mass_g (float): Saostunut massa grammoina (g)
    - density_g_cm3 (float): Pinnoitteen tiheys (g/cm³), esim. Cu = 8.96 g/cm³
    - area_dm2 (float): Pinnoitettava pinta-ala neliödesimetreinä (dm²)
    
    Palauttaa:
    - dict: Sisältää:
        'thickness_um' (float): Pinnoitteen paksuus mikrometreinä (µm)
        'calculation_steps' (str): Laskukaava ja vaiheet LaTeX-muodossa
    """
    # 1 dm² = 100 cm²
    area_cm2 = area_dm2 * 100
    
    # Tilavuus V = m / rho
    volume_cm3 = mass_g / density_g_cm3
    
    # Paksuus d = V / A (tuloksena cm, joka pitää muuttaa mikrometreiksi: 1 cm = 10 000 µm)
    thickness_cm = volume_cm3 / area_cm2
    thickness_um = thickness_cm * 10000
    
    latex_string = (
        f"Lasketaan pinnoitteen paksuus ($d$) kaavalla:\n"
        f"$$ d = \\frac{{m}}{{\\rho \\cdot A}} $$\n\n"
        f"Sijoitetaan arvot:\n"
        f"$$ d = \\frac{{{mass_g:.4f}\\text{{ g}}}}{{{density_g_cm3}\\text{{ g/cm}}^3 \\cdot ({area_dm2} \\cdot 100)\\text{{ cm}}^2}} $$\n\n"
        f"Tulos on senttimetreinä $ {thickness_cm:.6f} \\text{{ cm}} $. Muunnetaan mikrometreiksi ($ \\times 10000 $):\n"
        f"$$ d \\approx {thickness_um:.2f} \\text{{ }}\\mu\\text{{m}} $$"
    )
    
    return {
        "thickness_um": thickness_um,
        "calculation_steps": latex_string
    }

def current_density_calculation(current_a: float, area_dm2: float) -> dict:
    """
    Laskee virtatiheyden ampeereina per neliödesimetri (A/dm²).
    Tätä käytetään yleisesti elektrolyysikylpyjen ajoparametrien määrittelyssä.
    
    Argumentit:
    - current_a (float): Sähkövirta ampeereina (A)
    - area_dm2 (float): Pinta-ala neliödesimetreinä (dm²)
    
    Palauttaa:
    - dict: 'current_density_a_dm2', 'calculation_steps'
    """
    density = current_a / area_dm2
    
    latex_string = (
        f"Lasketaan virtatiheys ($J$ tai $i$):\n"
        f"$$ J = \\frac{{I}}{{A}} $$\n\n"
        f"$$ J = \\frac{{{current_a}\\text{{ A}}}}{{{area_dm2}\\text{{ dm}}^2}} $$\n\n"
        f"$$ J = {density:.2f} \\text{{ A/dm}}^2 $$"
    )
    
    return {
        "current_density_a_dm2": density,
        "calculation_steps": latex_string
    }


# ── SI-yksikkömuunnokset ──────────────────────────────────────────────

SI_PREFIXES = {
    "piko":  {"kerroin": 1e-12, "symboli": "p",  "potenssi": -12},
    "nano":  {"kerroin": 1e-9,  "symboli": "n",  "potenssi": -9},
    "mikro": {"kerroin": 1e-6,  "symboli": "µ",  "potenssi": -6},
    "milli": {"kerroin": 1e-3,  "symboli": "m",  "potenssi": -3},
    "sentti":{"kerroin": 1e-2,  "symboli": "c",  "potenssi": -2},
    "desi":  {"kerroin": 1e-1,  "symboli": "d",  "potenssi": -1},
    "perus": {"kerroin": 1e0,   "symboli": "",   "potenssi": 0},
    "deka":  {"kerroin": 1e1,   "symboli": "da", "potenssi": 1},
    "hehto": {"kerroin": 1e2,   "symboli": "h",  "potenssi": 2},
    "kilo":  {"kerroin": 1e3,   "symboli": "k",  "potenssi": 3},
    "mega":  {"kerroin": 1e6,   "symboli": "M",  "potenssi": 6},
    "giga":  {"kerroin": 1e9,   "symboli": "G",  "potenssi": 9},
}

# Englanninkieliset aliakset → suomenkielinen avain
_PREFIX_ALIASES = {
    "pico": "piko", "nano": "nano", "micro": "mikro",
    "milli": "milli", "centi": "sentti", "deci": "desi",
    "base": "perus", "deca": "deka", "hecto": "hehto",
    "kilo": "kilo", "mega": "mega", "giga": "giga",
}

def _resolve_prefix(name: str) -> str:
    """Resolve Finnish or English prefix name to canonical key."""
    key = name.strip().lower()
    return _PREFIX_ALIASES.get(key, key)


def unit_conversion(
    value: float,
    from_prefix: str,
    to_prefix: str,
    unit_symbol: str = ""
) -> dict:
    """
    Muuntaa arvon SI-etuliitteiden välillä.
    Tukee suomen- ja englanninkielisiä etuliitteitä.

    Tuetut etuliitteet (fi / en):
      piko/pico, nano, mikro/micro, milli, sentti/centi, desi/deci,
      perus/base (= ei etuliitettä), deka/deca, hehto/hecto,
      kilo, mega, giga

    Argumentit:
    - value (float): Muunnettava lukuarvo
    - from_prefix (str): Lähtöetuliite, esim. "milli"
    - to_prefix (str): Kohdeetuliite, esim. "kilo"
    - unit_symbol (str): Perusyksikkö, esim. "m" (metri), "g" (gramma), "A" (ampeeri)

    Esimerkkejä:
      unit_conversion(1500, "milli", "perus", "m")  → 1.5 m
      unit_conversion(2.5, "kilo", "perus", "g")     → 2500 g
      unit_conversion(0.003, "perus", "milli", "A")   → 3 mA
      unit_conversion(50, "sentti", "desi", "m")      → 5 dm
    """
    from_key = _resolve_prefix(from_prefix)
    to_key = _resolve_prefix(to_prefix)

    if from_key not in SI_PREFIXES:
        return {"error": f"Tuntematon lähtöetuliite: '{from_prefix}'. Tuetut: {', '.join(SI_PREFIXES.keys())}"}
    if to_key not in SI_PREFIXES:
        return {"error": f"Tuntematon kohdeetuliite: '{to_prefix}'. Tuetut: {', '.join(SI_PREFIXES.keys())}"}

    src = SI_PREFIXES[from_key]
    dst = SI_PREFIXES[to_key]

    # Muunnetaan perusyksikön kautta
    value_base = value * src["kerroin"]
    result = value_base / dst["kerroin"]

    # LaTeX-selitys
    from_sym = src["symboli"] + unit_symbol
    to_sym = dst["symboli"] + unit_symbol
    exponent_diff = src["potenssi"] - dst["potenssi"]

    latex_string = (
        f"SI-yksikkömuunnos:\n"
        f"$$ {value}\\text{{ {from_sym}}} "
        f"= {value} \\times 10^{{{src['potenssi']}}} \\text{{ {unit_symbol}}} "
        f"= {value_base:.6g} \\text{{ {unit_symbol}}} $$\n\n"
        f"Muunnetaan kohdeyksikköön ($ 10^{{{dst['potenssi']}}} $):\n"
        f"$$ {value_base:.6g} \\div 10^{{{dst['potenssi']}}} "
        f"= {result:.6g} \\text{{ {to_sym}}} $$\n\n"
        f"Tulos:\n"
        f"$$ {value}\\text{{ {from_sym}}} = {result:.6g}\\text{{ {to_sym}}} $$"
    )

    return {
        "result": result,
        "from": f"{value} {from_sym}",
        "to": f"{result:.6g} {to_sym}",
        "calculation_steps": latex_string
    }
