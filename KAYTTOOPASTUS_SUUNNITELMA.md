# Käyttöopastuksen suunnitelma

## A. Koodista generoitu dokumentaatio

### Tavoite

Automatisoida sovelluksen käyttödokumentaation tuottaminen lähdekoodin
perusteella. LLM analysoi koodin ja generoi englanninkieliset
toimintakuvaukset, jotka tallennetaan vektoritietokantaan ja/tai
käytetään suoraan in-app-opastuksessa.

### Skannattavat koodikerrokset

```
Sovelluksen lähdekoodi
│
├── Frontend (UI-komponentit)
│   ├── Reitit / sivut       → Navigointirakenne, sivukartta
│   ├── Lomakkeet            → Kenttäkuvaukset, validoinnit, pakollisuudet
│   ├── Napit / toiminnot    → Käytettävissä olevat toiminnot per näkymä
│   ├── Dialogit / modalit   → Vahvistukset, varoitukset
│   ├── Taulukot / listat    → Mitä dataa näytetään, sarakkeet
│   ├── i18n-avaimet         → UI-tekstit (näkyvä teksti)
│   └── Käyttöoikeudet (UI)  → Mitkä elementit näkyvät millekin roolille
│
├── Backend (API)
│   ├── Endpointit           → Toiminnot, HTTP-metodit, parametrit
│   ├── Validointisäännöt    → Kenttien rajoitukset, virheilmoitukset
│   ├── Roolit / oikeudet    → Kuka saa tehdä mitä
│   ├── Tietomalli           → Käsitteet ja niiden suhteet
│   └── Virheviestit         → Virhekoodit + selitykset
│
└── PLC / automaatio (jos sovellettavissa)
    ├── Function blockit     → Toimintalogiikka
    ├── Tyyppimäärittelyt    → Datamallit
    └── Konfiguraatio        → Asetukset, vakiot
```

### Generointiprosessi

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  1. SKANNAUS                                                   │
│     scripts/scan_code.py                                       │
│     ├── AST-parsinta (Abstract Syntax Tree)                    │
│     │   → Komponenttien, funktioiden, luokkien tunnistus       │
│     │   → Ei tarvitse ajaa koodia, pelkkä staattinen analyysi  │
│     ├── Reittikartta                                           │
│     │   → React Router / Vue Router / Flask routes             │
│     ├── Lomakekenttien poimiminen                              │
│     │   → input-elementit, label, placeholder, validation      │
│     └── API-endpointit                                         │
│         → Dekoraattorit (@app.get, @router.post)               │
│                                                                │
│  2. KONTEKSTIN KOOSTAMINEN                                     │
│     Jokaisesta komponentista / moduulista:                     │
│     {                                                          │
│       "file": "src/components/RecipeForm.tsx",                 │
│       "type": "form-component",                                │
│       "route": "/settings/recipes/new",                        │
│       "fields": [                                              │
│         {"name": "name", "type": "text", "required": true},   │
│         {"name": "bathType", "type": "select", "options": [...]│
│       ],                                                       │
│       "actions": ["save", "cancel"],                           │
│       "validations": ["name required", "thickness 0.1-500"],   │
│       "source_code": "... (koko tiedosto tai relevantit osat)" │
│     }                                                          │
│                                                                │
│  3. LLM-GENEROINTI                                             │
│     scripts/generate_docs.py                                   │
│     ├── System prompt: "Generate user documentation..."        │
│     ├── Input: komponenttikonteksti (yllä)                     │
│     ├── Output: strukturoitu Markdown                          │
│     └── Tallennus: docs/ + vektoritietokanta                   │
│                                                                │
│  4. TARKISTUS                                                  │
│     ├── Automaattinen: onko kaikki kentät dokumentoitu?        │
│     └── Manuaalinen: ihminen tarkistaa ennen julkaisua         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### LLM:n system prompt koodiskannaukseen

```
You are a technical documentation generator. Analyze the provided 
application source code and generate user-facing documentation.

Output format for each component:

1. PAGE TITLE — The name of the view/page
2. NAVIGATION — How to reach this page (menu path)
3. PURPOSE — What the user can do here (1-2 sentences)
4. FIELDS — Table: field name, type, required, constraints, description
5. ACTIONS — Available buttons/operations and what they do
6. WORKFLOW — Numbered steps for the primary task
7. COMMON ERRORS — Validation messages and what to do
8. RELATED — Links to related views/functions
9. UI_SELECTORS — CSS selectors for each interactive element
   (used for in-app guidance tours)

Write for end users (plant operators), not developers.
All output must be in English.
```

### Generoitavan dokumentin rakenne

Jokaisesta näkymästä syntyy:

```json
{
  "page_id": "recipe-management",
  "title": "Recipe Management",
  "navigation": "Settings → Recipes",
  "purpose": "Create, edit, and manage plating recipes that define process parameters for each bath type.",
  "fields": [
    {
      "name": "Recipe Name",
      "selector": "#recipe-name",
      "type": "text",
      "required": true,
      "constraints": "Cannot be empty, must be unique",
      "description": "A descriptive name for this recipe, e.g. 'Watts Nickel 25µm'"
    }
  ],
  "actions": [
    {
      "name": "New Recipe",
      "selector": "button.new-recipe",
      "description": "Opens the recipe creation form"
    },
    {
      "name": "Save",
      "selector": "button.save",
      "description": "Saves the recipe to the database"
    }
  ],
  "workflow": [
    "Navigate to Settings → Recipes",
    "Click 'New Recipe'",
    "Fill in the required fields",
    "Click 'Save'"
  ],
  "errors": [
    {
      "message": "Name is required",
      "cause": "Recipe name field is empty",
      "solution": "Enter a descriptive name for the recipe"
    }
  ],
  "tour_steps": [
    {
      "selector": "#nav-recipes",
      "title": "Recipe Menu",
      "text": "Click here to open recipe management.",
      "position": "right",
      "wait_for_click": true
    }
  ]
}
```

### Koodi ↔ dokumentaatio -mappaus

```yaml
# docs/doc-map.yaml

mappings:
  # Frontend-komponentti → dokumentaatio + tour
  - source: src/components/RecipeForm.tsx
    doc_id: recipe-management
    tour_id: tour-recipe-create
    screenshots:
      - recipe-list
      - recipe-form
      - recipe-validation

  - source: src/components/ReportView.tsx
    doc_id: reporting
    tour_id: tour-reporting
    screenshots:
      - report-main
      - report-filters

  - source: src/api/recipes.py
    doc_id: recipe-management
    # Backend tukee samaa dokumentaatiota kuin frontend

  # PLC-koodi → proprietary-dokumentaatio
  - source: plc/src/STC_FB_MainScheduler.st
    doc_id: plc-main-scheduler
    access_level: proprietary
```

### Muutostunnistus ja automaattinen päivitys

```
┌────────────────────────────────────────────────────────────┐
│  Git push → CI pipeline                                    │
│                                                            │
│  1. git diff --name-only HEAD~1                            │
│     → Mitkä tiedostot muuttuivat?                          │
│                                                            │
│  2. doc-map.yaml → mitkä dokumentit vaikuttuvat?           │
│     RecipeForm.tsx muuttui → recipe-management päivitettävä│
│                                                            │
│  3. Aja koodiskannaus muuttuneille komponenteille           │
│     → Uusi kenttä? Poistettu validointi? Uusi nappi?       │
│                                                            │
│  4. LLM vertaa vanhaa ja uutta dokumentaatiota             │
│     → Generoi diff: "Added field: Customer Reference"      │
│                                                            │
│  5. Päivitä:                                               │
│     a) docs/{doc_id}.json — dokumentaatio                  │
│     b) tours/{tour_id}.json — opastusaskeleet              │
│     c) Vektoritietokanta — päivitetyt chunkit              │
│                                                            │
│  6. Luo PR: "docs: auto-update recipe-management"          │
│     → Ihminen tarkistaa ja hyväksyy                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Tiedostorakenne

```
docs/
├── doc-map.yaml                    ← koodi ↔ dokumentaatio -mappaus
├── pages/
│   ├── recipe-management.json      ← generoitu dokumentaatio
│   ├── reporting.json
│   ├── user-admin.json
│   └── dashboard.json
├── tours/
│   ├── tour-welcome.json           ← tervetuliaisopastus
│   ├── tour-recipe-create.json     ← reseptien luonti
│   ├── tour-reporting.json         ← raportointi
│   └── tour-admin.json             ← ylläpito
└── scripts/
    ├── scan_code.py                ← koodiskannaus (AST)
    ├── generate_docs.py            ← LLM-generointi
    ├── update_tours.py             ← tour-konfiguraation päivitys
    └── detect_changes.py           ← muutostunnistus (CI)
```

---

## B. In-app-opastus (Interactive UI Guidance)

### Tavoite

Toteuttaa interaktiivinen, sovelluksen sisäinen opastus, joka:
- Korostaa UI-elementtejä ja näyttää ohjeet puhekuplassa
- Ohjaa käyttäjää vaihe vaiheelta oikean toiminnon läpi
- Mukautuu käyttäjän rooliin ja kokemustasoon
- Päivittyy automaattisesti koodiskannauksen perusteella

### Kirjastovalinta

| Kirjasto | Koko | Lisenssi | Framework | Suositus |
|----------|------|----------|-----------|----------|
| **Driver.js** | ~5 KB | MIT | Vanilla JS | ✅ Kevyin, riittävä |
| **Shepherd.js** | ~30 KB | MIT | Vanilla JS | ✅ Monipuolisin |
| **React Joyride** | ~40 KB | MIT | React | Jos React-sovellus |
| **Intro.js** | ~20 KB | AGPL/kaupal. | Vanilla JS | ⚠️ Lisenssi |

**Suositus:** Shepherd.js (monipuolinen, MIT) tai Driver.js (kevyt, MIT).
Valinta riippuu kohdesovelluksen frameworkista.

### Opastuksen arkkitehtuuri

```
┌─────────────────────────────────────────────────────────────┐
│  Sovellus (Browser)                                         │
│                                                             │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐ │
│  │  Sovelluksen  │  │  Tour Engine  │  │  Help Chat       │ │
│  │  normaali UI  │  │  (Shepherd/   │  │  (valinnainen)   │ │
│  │               │  │   Driver.js)  │  │                  │ │
│  │               │  │              │  │  "Miten teen X?" │ │
│  │  ┌─────────┐  │  │  tour.json   │  │  → käynnistää    │ │
│  │  │ ?-nappi │──┼──┤  → askeleet  │  │    tourin         │ │
│  │  └─────────┘  │  │  → highlight │  │                  │ │
│  │               │  │  → tooltips  │  │                  │ │
│  └──────────────┘  └───────┬───────┘  └────────┬─────────┘ │
│                            │                   │            │
│                     ┌──────┴───────────────────┘            │
│                     │                                       │
│                     ▼                                       │
│              Tour Registry                                  │
│              ┌─────────────────────┐                        │
│              │ tours/              │                        │
│              │ ├── welcome.json    │  ← staattiset tourit   │
│              │ ├── recipes.json    │                        │
│              │ └── reporting.json  │                        │
│              │                     │                        │
│              │ API: /api/guide     │  ← AI-generoitu tour   │
│              │ (LLM + Qdrant)     │    (dynaaminen)        │
│              └─────────────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Opastustyypit

#### 1. Welcome Tour (ensimmäinen kirjautuminen)

```json
{
  "id": "tour-welcome",
  "trigger": "first_login",
  "title": "Welcome to the Application",
  "steps": [
    {
      "selector": "#sidebar",
      "title": "Navigation",
      "text": "Use the sidebar to navigate between sections.",
      "position": "right"
    },
    {
      "selector": "#nav-dashboard",
      "title": "Dashboard",
      "text": "Your overview of current production status.",
      "position": "right"
    },
    {
      "selector": "#nav-recipes",
      "title": "Recipes",
      "text": "Manage plating recipes and process parameters.",
      "position": "right"
    },
    {
      "selector": "#user-menu",
      "title": "Your Profile",
      "text": "Access settings, preferences, and sign out here.",
      "position": "bottom"
    }
  ]
}
```

#### 2. Task Tour (toiminnon opastus)

```json
{
  "id": "tour-recipe-create",
  "trigger": "manual",
  "title": "Creating a New Recipe",
  "context_page": "/settings/recipes",
  "steps": [
    {
      "selector": "button.new-recipe",
      "title": "Step 1: New Recipe",
      "text": "Click this button to start creating a new recipe.",
      "position": "bottom",
      "wait_for_click": true,
      "highlight": true
    },
    {
      "selector": "#recipe-name",
      "title": "Step 2: Recipe Name",
      "text": "Enter a descriptive name, e.g. 'Watts Nickel 25µm'. This must be unique.",
      "position": "right",
      "input_hint": "Watts Nickel 25µm"
    },
    {
      "selector": "#bath-type",
      "title": "Step 3: Bath Type",
      "text": "Select the bath type. This determines available parameters.",
      "position": "right"
    },
    {
      "selector": "#thickness",
      "title": "Step 4: Target Thickness",
      "text": "Set the target coating thickness in µm (0.1–500).",
      "position": "right"
    },
    {
      "selector": "button.save",
      "title": "Step 5: Save",
      "text": "Click Save to store the recipe. You can edit it later.",
      "position": "top",
      "wait_for_click": true
    }
  ]
}
```

#### 3. Feature Tour (uusi ominaisuus)

```json
{
  "id": "tour-feature-v2.2",
  "trigger": "version_first_login",
  "trigger_version": "2.2.0",
  "title": "What's New in Version 2.2",
  "dismissable": true,
  "steps": [
    {
      "selector": "#recipe-copy-btn",
      "title": "New: Copy Recipe",
      "text": "You can now duplicate an existing recipe as a starting point.",
      "position": "bottom",
      "badge": "NEW"
    },
    {
      "selector": "#batch-export",
      "title": "New: Batch Export",
      "text": "Export multiple reports at once as PDF or CSV.",
      "position": "left",
      "badge": "NEW"
    }
  ]
}
```

#### 4. Contextual Tooltips (aina saatavilla)

```json
{
  "id": "tooltips-recipe-form",
  "trigger": "page_load",
  "context_page": "/settings/recipes/*",
  "type": "tooltips",
  "hints": [
    {
      "selector": "#current-density-min",
      "icon": "ℹ️",
      "text": "Minimum current density in A/dm². Typical range for Watts nickel: 2–5 A/dm².",
      "position": "right"
    },
    {
      "selector": "#temperature",
      "icon": "ℹ️",
      "text": "Bath operating temperature in °C. Watts nickel typically runs at 45–65 °C.",
      "position": "right"
    }
  ]
}
```

#### 5. Error Recovery (virheopastus)

```json
{
  "id": "error-recipe-save-failed",
  "trigger": "error",
  "error_code": "RECIPE_DUPLICATE_NAME",
  "steps": [
    {
      "selector": "#recipe-name",
      "title": "Duplicate Name",
      "text": "A recipe with this name already exists. Change the name or add a suffix (e.g. '-v2').",
      "position": "right",
      "highlight": true,
      "style": "error"
    }
  ]
}
```

### Frontend-integraatio

#### Tour Engine -komponentti

```javascript
// src/guidance/TourEngine.js

import Shepherd from 'shepherd.js';
import 'shepherd.js/dist/css/shepherd.css';

class TourEngine {
  constructor() {
    this.tours = {};
    this.completedTours = this.loadCompleted();
  }

  // Rekisteröi tour JSON-konfiguraatiosta
  register(tourConfig) {
    this.tours[tourConfig.id] = tourConfig;
  }

  // Lataa tourit palvelimelta
  async loadTours() {
    const response = await fetch('/api/tours');
    const tours = await response.json();
    tours.forEach(t => this.register(t));
  }

  // Käynnistä nimetty tour
  start(tourId) {
    const config = this.tours[tourId];
    if (!config) return;

    const tour = new Shepherd.Tour({
      defaultStepOptions: {
        cancelIcon: { enabled: true },
        scrollTo: { behavior: 'smooth', block: 'center' }
      },
      useModalOverlay: true
    });

    config.steps.forEach((step, index) => {
      const isLast = index === config.steps.length - 1;
      
      tour.addStep({
        id: `${tourId}-step-${index}`,
        title: step.title,
        text: step.text,
        attachTo: { 
          element: step.selector, 
          on: step.position || 'bottom' 
        },
        advanceOn: step.wait_for_click
          ? { selector: step.selector, event: 'click' }
          : undefined,
        buttons: step.wait_for_click ? [] : [
          ...(index > 0 ? [{
            text: 'Back', action: tour.back, secondary: true
          }] : []),
          {
            text: isLast ? 'Done' : 'Next',
            action: isLast ? tour.complete : tour.next
          }
        ]
      });
    });

    tour.on('complete', () => this.markCompleted(tourId));
    tour.on('cancel', () => this.markCompleted(tourId));
    tour.start();
  }

  // AI-pohjainen dynaaminen tour
  async startAIGuide(question) {
    const response = await fetch('/api/guide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        current_page: window.location.pathname,
        user_role: this.getUserRole()
      })
    });

    const { tour_config } = await response.json();
    this.register(tour_config);
    this.start(tour_config.id);
  }

  // Automaattinen trigger-tarkistus sivun latautuessa
  checkAutoTriggers() {
    const page = window.location.pathname;
    const version = this.getAppVersion();

    for (const [id, config] of Object.entries(this.tours)) {
      if (this.completedTours.includes(id)) continue;

      switch (config.trigger) {
        case 'first_login':
          if (this.isFirstLogin()) this.start(id);
          break;
        case 'version_first_login':
          if (version === config.trigger_version) this.start(id);
          break;
        case 'page_load':
          if (this.matchPage(page, config.context_page)) {
            this.showTooltips(config);
          }
          break;
      }
    }
  }

  // Tooltip-hintit (ℹ️ ikonit kenttien vieressä)
  showTooltips(config) {
    config.hints?.forEach(hint => {
      const el = document.querySelector(hint.selector);
      if (!el) return;

      const icon = document.createElement('span');
      icon.className = 'guidance-hint-icon';
      icon.textContent = hint.icon || 'ℹ️';
      icon.title = hint.text;
      icon.addEventListener('click', () => {
        // Näytä tooltip Shepherd-tyylillä
        const tip = new Shepherd.Tour({ useModalOverlay: false });
        tip.addStep({
          text: hint.text,
          attachTo: { element: hint.selector, on: hint.position },
          buttons: [{ text: 'OK', action: tip.complete }]
        });
        tip.start();
      });

      el.parentNode.insertBefore(icon, el.nextSibling);
    });
  }

  // Virhe-trigger
  onError(errorCode) {
    const errorTour = Object.values(this.tours)
      .find(t => t.trigger === 'error' && t.error_code === errorCode);
    if (errorTour) this.start(errorTour.id);
  }

  // Persistenssi: mitkä tourit käyttäjä on jo nähnyt
  loadCompleted() {
    return JSON.parse(localStorage.getItem('completed_tours') || '[]');
  }
  markCompleted(tourId) {
    this.completedTours.push(tourId);
    localStorage.setItem('completed_tours', 
      JSON.stringify(this.completedTours));
  }
}

export default TourEngine;
```

#### Help-nappi (? -ikoni)

```javascript
// Jokaiselle sivulle:
const helpButton = document.createElement('button');
helpButton.className = 'help-fab';       // Floating Action Button
helpButton.textContent = '?';
helpButton.addEventListener('click', () => {
  // Näytä valikko:
  // 1. "Show me around this page" → staattinen tour
  // 2. "Ask a question" → AI-chat + dynaaminen tour
  // 3. "What's new" → feature tour
  showHelpMenu();
});
document.body.appendChild(helpButton);
```

### Backend: AI-pohjainen opastus

```python
# API: /api/guide — dynaaminen tour LLM:llä

@app.post("/api/guide")
async def generate_guide(request: GuideRequest):
    """
    Generoi interaktiivinen UI-opastus käyttäjän kysymyksen perusteella.
    
    1. Hakee relevantin dokumentaation Qdrantista
    2. LLM generoi tour-askeleet CSS-selektoreineen
    3. Palauttaa Shepherd.js-yhteensopivan tour-konfiguraation
    """
    
    # 1. Vektorihaku — etsi relevantti dokumentaatio
    docs = search_qdrant(
        query=request.question,
        filter={"context_page": request.current_page}  # rajaa nykyiseen sivuun
    )
    
    # 2. LLM generoi tour-askeleet
    response = llm.chat.completions.create(
        model="...",
        messages=[
            {
                "role": "system",
                "content": GUIDE_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"User question: {request.question}\n"
                           f"Current page: {request.current_page}\n"
                           f"User role: {request.user_role}\n"
                           f"Documentation context:\n{docs}"
            }
        ],
        response_format={"type": "json_object"}
    )
    
    tour_config = json.loads(response.choices[0].message.content)
    return {"tour_config": tour_config}


GUIDE_SYSTEM_PROMPT = """You are an in-app guidance generator. Based on the user's 
question and the documentation context, generate an interactive UI tour.

Return JSON with this structure:
{
  "id": "ai-guide-{timestamp}",
  "title": "...",
  "steps": [
    {
      "selector": "CSS selector for the UI element",
      "title": "Step title",
      "text": "1-2 sentence instruction",
      "position": "top|bottom|left|right",
      "wait_for_click": true/false
    }
  ]
}

Rules:
- Use precise CSS selectors that match the application's DOM
- Keep step text concise and action-oriented
- Use wait_for_click=true for steps where the user must interact
- Maximum 8 steps per tour
- If the question cannot be answered with a tour, return:
  {"id": "...", "title": "...", "steps": [], 
   "message": "This requires a text explanation rather than a tour."}
"""
```

### Käyttäjäkokemus

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Ensimmäinen kirjautuminen                                  │
│  → Welcome Tour käynnistyy automaattisesti                  │
│  → Käyttäjä voi skipata: "Skip tour" / "Don't show again"   │
│                                                             │
│  Normaalikäyttö                                             │
│  → ℹ️ ikonit kenttien vieressä (hover = selitys)             │
│  → ? FAB-nappi oikeassa alanurkassa                         │
│       → "Show me around" → sivukohtainen tour               │
│       → "Ask a question" → AI-chat → dynaaminen tour        │
│                                                             │
│  Virhetilanne                                               │
│  → Lomakkeen validointi epäonnistuu                          │
│  → Tour korostaa ongelma-kentän ja selittää virheen          │
│                                                             │
│  Uusi versio                                                │
│  → Feature Tour: "What's New" käynnistyy automaattisesti    │
│  → Korostaa uudet/muuttuneet elementit                      │
│                                                             │
│  Admin-käyttäjä                                             │
│  → Näkee admin-toimintojen tourit                            │
│  → Voi muokata tour-konfiguraatioita (hallintapaneeli)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Analytiikka

Tour-dataa kerätään parantamista varten:

```json
{
  "event": "tour_step_viewed",
  "tour_id": "tour-recipe-create",
  "step_index": 2,
  "user_role": "operator",
  "timestamp": "2026-03-11T10:30:00Z"
}

{
  "event": "tour_completed",
  "tour_id": "tour-recipe-create",
  "steps_viewed": 5,
  "steps_total": 5,
  "duration_seconds": 45
}

{
  "event": "tour_abandoned",
  "tour_id": "tour-welcome",
  "abandoned_at_step": 3,
  "steps_total": 5
}
```

Tämän perusteella nähdään:
- Mitkä tourit skipattaan usein → liian pitkiä tai turhia
- Missä askeleessa käyttäjät keskeyttävät → epäselvä ohje
- Mitkä AI-kysymykset toistuvat → lisää staattisiksi toureiksi

---

## Toteutusjärjestys

| Vaihe | Kuvaus | Riippuvuudet | Arvio |
|-------|--------|-------------|-------|
| **1** | Shepherd.js/Driver.js integrointi | Kohdesovellus | 4 h |
| **2** | Welcome Tour + 2–3 Task Touria (staattinen JSON) | Vaihe 1 | 8 h |
| **3** | Contextual tooltips (ℹ️ ikonit) | Vaihe 1 | 4 h |
| **4** | Help FAB-nappi (?) ja tour-valikko | Vaihe 1 | 4 h |
| **5** | Koodiskannausskripti (scan_code.py) | Lähdekoodin saatavuus | 8 h |
| **6** | LLM-generointi (generate_docs.py) | Vaihe 5 + LLM-yhteys | 8 h |
| **7** | doc-map.yaml + muutostunnistus | Vaihe 5, 6 | 4 h |
| **8** | AI-pohjainen dynaaminen tour (/api/guide) | Vaihe 1 + LLM + Qdrant | 8 h |
| **9** | Error Recovery -tourit | Vaihe 1 | 4 h |
| **10** | Feature Tour -järjestelmä (versiokohtainen) | Vaihe 1 | 4 h |
| **11** | CI-integraatio (automaattinen päivitys) | Vaihe 5, 6, 7 | 8 h |
| **12** | Analytiikka (käyttödata) | Vaihe 1 | 4 h |
| | **YHTEENSÄ** | | **~68 h** |

### Vaiheittainen eteneminen

```
MVP (Vaiheet 1–4):              ~20 h
  Staattinen in-app-opastus toimii.
  Käyttäjä saa welcome tour + task tours + tooltips.

Automaatio (Vaiheet 5–7):       ~20 h
  Koodiskannaus + LLM-generointi toimii.
  Dokumentaatio pysyy ajan tasalla.

AI-opastus (Vaiheet 8–10):      ~16 h
  Käyttäjä voi kysyä "Miten teen X?" ja
  saa dynaamisen opastuksen.

Tuotanto (Vaiheet 11–12):       ~12 h
  CI-putkessa, analytiikka kertoo
  mikä toimii ja mikä ei.
```

---

## Yhteys muihin suunnitelmiin

| Suunnitelma | Yhteys |
|---|---|
| [TIETOKANNAN_RIKASTUS.md](TIETOKANNAN_RIKASTUS.md) | Generoidut kuvaukset tallennetaan vektori-DB:hen (access_level = proprietary) |
| [CALC_RIKASTUS.md](CALC_RIKASTUS.md) | Tooltipeissä voidaan viitata calc-funktioihin ("Thickness calculated using Faraday's law") |
| [ARCHITECTURE.md](ARCHITECTURE.md) | In-app-opastus on uusi komponentti arkkitehtuurissa |

## Teknologiavalinnat (yhteenveto)

| Komponentti | Valinta | Perustelu |
|---|---|---|
| Tour-kirjasto | Shepherd.js | MIT, monipuolinen, framework-agnostinen |
| Koodiskannaus | Python AST + custom parsers | Ei ulkoisia riippuvuuksia |
| Dokumentaatiogenerointi | LLM (lokaali tai Azure OpenAI) | Sama kuin muussa järjestelmässä |
| Tour-konfiguraatio | JSON-tiedostot + API | Versionhallittu, päivitettävä |
| Kontekstitieto | Qdrant / pgvector | Riippuu kohdejärjestelmästä |
| CI/CD | GitHub Actions | Automaattinen päivitys |
