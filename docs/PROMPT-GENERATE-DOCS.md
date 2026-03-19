# Prompt: Generera dokumentation för Automower Trade-in Form

**Kör denna prompt i en AI-modell** (t.ex. ChatGPT, Claude, etc.) tillsammans med projektets filer eller repo-länk. Be modellen generera dokumentation som du sedan kan exportera till PDF.

---

## Prompt (kopiera och klistra in)

```
Generera en komplett tekniskt dokumentationsdokument för lösningen "Automower Trade-in Form" – en webbapplikation där återförsäljare (dealers) kan skicka in trade-in-ansökningar för Automower-robotgräsklippare.

### Innehåll som ska ingå

1. **Översikt**
   - Syfte och användningsfall
   - Målgrupp (dealers/återförsäljare)
   - Språk: engelska (en) och österrikisk tyska (de-AT)

2. **Arkitektur**
   - Stack: Python 3.12, FastAPI, SQLite, statisk HTML/CSS/JS frontend
   - Deployment: Docker → Azure DevOps → Husqvarna DevPlatform (OpenShift)
   - Port: 4001
   - URL-routing: /en, /de-at för direktlänkning till språk

3. **Funktionalitet**
   - Formulär för dealer-data och produktinfo (sålt modell, serienummer, trade-in-typ)
   - Filuppladdning: namnskylt, produktbild, faktura (max 25 MB, .png/.jpg/.jpeg/.pdf)
   - Admin-panel via SSO (Microsoft Entra)
   - Excel-export av submissioner
   - Valfri n8n-webhook för integrationer

4. **Konfiguration**
   - Miljövariabler (AUTH_CLIENT_ID, AUTH_REDIRECT_URI, AUTH_SERVER_METADATA_URL, etc.)
   - Key Vault för secrets (AUTH_CLIENT_SECRET, AUTH_COOKIE_SECRET)
   - config/.env.dev och config/.env.prod

5. **Deployment**
   - Azure Pipelines (main-branch trigger)
   - Dev- och prod-URL:er enligt Husqvarna DevPlatform-mönster
   - Persistent storage för DB och uploads

6. **Lokal utveckling**
   - docker-compose up
   - Eller uvicorn backend.app:app --reload --port 4001

### Design och stil – VIKTIGT

Använd **Husqvarna varumärkesstil** enligt design systemet här:
https://wonderful-coast-058f9fd03.1.azurestaticapps.net/?path=/docs/welcome--docs

- Inkludera Husqvarna-logotyp i header/försättsblad
- Färgpalett: Husqvarna-grön (#273417 eller liknande), neutrala gråtoner, vit bakgrund
- Typografi: Helvetica Neue eller system fonts som i referensen
- Professionellt, rent och lättläst layout
- Sektioner med tydliga rubriker, tabeller där lämpligt

### Utdataformat

Generera dokumentationen som **HTML** med inbäddad CSS så att:
1. Den kan öppnas i webbläsare
2. Den ser professionell ut med Husqvarna-stil
3. Användaren kan skriva ut till PDF via webbläsarens "Skriv ut" → "Spara som PDF"

Eller generera **Markdown** som lätt kan konverteras till PDF med t.ex. Pandoc eller en MD→PDF-verktyg.

Om du genererar HTML: inkludera en print-vänlig CSS (@media print) för bra PDF-utskrift.
```

---

## Hur du får fram PDF

### Alternativ 1: HTML → PDF (rekommenderas)
1. Kör prompten i AI-modellen med projektkontext
2. Spara den genererade HTML-filen (t.ex. `docs/tradein-form-documentation.html`)
3. Öppna filen i webbläsaren (Chrome, Edge, Safari)
4. **Filställning** → **Skriv ut** → Välj **Spara som PDF** → Spara

### Alternativ 2: Markdown → PDF
1. Spara genererad Markdown till `docs/tradein-form-documentation.md`
2. Konvertera med Pandoc:
   ```bash
   pandoc docs/tradein-form-documentation.md -o docs/tradein-form-documentation.pdf --pdf-engine=wkhtmltopdf
   ```
3. Eller använd [md-to-pdf](https://www.npmjs.com/package/md-to-pdf), [Grip](https://github.com/joeyes/grip) eller liknande

### Alternativ 3: Word → PDF
Om AI:n genererar Word (.docx) kan du öppna i Word/LibreOffice och exportera till PDF.

---

## Kontext du kan bifoga till prompten

Ge AI-modellen åtkomst till (eller klistra in innehåll från):
- `docs/DEPLOY-HUSQVARNA-DEVPLATFORM.md`
- `docs/PRODUCTION-READINESS.md`
- `README.md` (om det finns)
- `backend/app.py` (översikt av endpoints)
- `index.html` och `script.js` (formulärstruktur)
- `azure-pipelines.yml`
- `config/README.md`
