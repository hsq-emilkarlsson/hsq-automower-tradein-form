# Produktionsredo – Automower Trade-in Form

## Genomförd granskning (2025-03-12)

### ✅ Säkerhet

| Punkt | Status |
|------|--------|
| Secrets via Key Vault (`\|DOMAIN\|`) | OK |
| `.env` ignoreras i git | OK |
| `config/.env.*` innehåller endast placeholders | OK |
| Session: `https_only` i produktion | Fixad |
| Session secret-varning om tomt i prod | Tillagd |
| Filuppladdning: filtyp-whitelist (.png, .jpg, .jpeg, .pdf) | Tillagd |
| Filuppladdning: max 25 MB | Tillagd |
| Admin: SSO eller token, `secrets.compare_digest` | OK |

### ✅ Backend

| Punkt | Status |
|------|--------|
| Healthz (v2-format för DevPlatform) | OK |
| Liveness/readiness-probes | OK |
| Loggning (LOG_LEVEL) | Tillagd |
| n8n webhook-fel loggas | Tillagd |
| Dependencies med versionsintervall | Tillagd |

### ✅ Infrastruktur

| Punkt | Status |
|------|--------|
| Dockerfile: Python 3.12-slim | OK |
| Port 4001 (DevPlatform) | OK |
| HEALTHCHECK i Dockerfile | OK |
| Azure Pipelines (main → deploy) | OK |
| .dockerignore exkluderar .env | OK |

### ⚠️ Kvar att verifiera före prod

1. **SSO-konfiguration**: Fyll i `config/.env.prod` med:
   - `AUTH_CLIENT_ID` – Entra-appens Client ID
   - `AUTH_REDIRECT_URI` – t.ex. `https://<din-prod-url>/oauth2callback`
   - `AUTH_SERVER_METADATA_URL` – Entra discovery URL
   - Key Vault måste ha: `AUTH_CLIENT_SECRET`, `AUTH_COOKIE_SECRET`

2. **PUBLIC_BASE_URL**: Sätt till den publika prod-URL:en så att länkar i Excel-export och fil-URL:er blir korrekta.

3. **Data**: Kontrollera att `data/` och `uploads/` inte committas till git (de ska vara i .gitignore – men ADO-repot kan ha haft dem i merge).

---

## Kör lokalt

```bash
cp .env.example .env
# Redigera .env med ADMIN_ACCESS_TOKEN
uvicorn backend.app:app --reload --port 4001
```

## Checklista före prod-deploy

- [ ] SSO är konfigurerat eller ADMIN_ACCESS_TOKEN är satt
- [ ] `PUBLIC_BASE_URL` satt till prod-URL
- [ ] `ENVIRONMENT=prod` i prod-config (redan tillagt)
- [ ] Key Vault har AUTH_CLIENT_SECRET och AUTH_COOKIE_SECRET (vid SSO)
