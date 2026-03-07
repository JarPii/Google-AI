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
