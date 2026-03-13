# Config – DevPlatform

Config-mappen behålls enligt plattformskrav. Här specar du miljövariabler för dev/prod.

## Secrets (Key Vault)

För hemligheter: sätt värdet till `|DOMAIN|` – plattformen hämtar då från Key Vault.

Du kan inte skriva till Key Vault själv – ge värdena till kollegan så lägger de in dem.

**Värden som behövs i Key Vault (endast SSO):**
- `AUTH_CLIENT_SECRET` – Entra SSO
- `AUTH_COOKIE_SECRET` – session-cookie

**Kan sättas direkt i config (inte hemligt):**
- `AUTH_CLIENT_ID` – Entra appens Client ID
- `AUTH_REDIRECT_URI` – callback-URL per miljö
- `AUTH_SERVER_METADATA_URL` – Entra OpenID Discovery-URL

**Entra-app: Lägg till redirect URIs**
- Dev: `https://tradein-automower-tradetermform.dev.devplatform.husqvarna-online.net/oauth2callback`
- Prod: `https://tradein-automower-tradetermform.prod.devplatform.husqvarna-online.net/oauth2callback`

## Health endpoints (krävs av plattformen)

- `/healthz` – full JSON med buildId (v2-format)
- `/healthz/liveness` – returnerar `UP`
- `/healthz/readiness` – samma som `/healthz`
