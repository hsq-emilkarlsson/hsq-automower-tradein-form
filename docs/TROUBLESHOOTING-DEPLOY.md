# Felsökning: Deploy och health check

## Symptom

Pipeline:en kör Ping-steget men får:
- `Health check response is in v1 format` (när gammal kod körs)
- `TypeError: Cannot read properties of undefined (reading 'buildId')`
- Eller: buildId i svar (t.ex. 209035) matchar inte förväntat (t.ex. 209036)

## Verifierat

- **Appen fungerar**: `curl https://tradein-automower-tradetermform.dev.devplatform.husqvarna-online.net/healthz` returnerar v2-format korrekt
- **healthz-implementationen är rätt**: status, version 2, info { buildId, buildNumber, sourceVersion, … }
- **Plattformen injicerar env vars**: BUILD_ID, SOURCE_VERSION, etc. sätts av DevPlatform vid deploy

## Rotorsak: Timing vid rolling update

```
[Deploy step klar] → [Ping körs direkt] → [Nya pods inte i rotation än] → FEL
```

1. Deploy-step uppdaterar Kubernetes Deployment med ny image
2. Kubernetes startar nya pods (rolling update)
3. Ping körs nästan samtidigt
4. Load balancern skickar fortfarande trafik till **gamla** pods
5. Ping får svar från gamla pods med tidigare `buildId`
6. CLI kräver att `response.info.buildId === förväntat build-id` → mismatch → fel

## Verifieringssteg

### 1. Kontrollera vad som faktiskt körs

```bash
curl -s https://tradein-automower-tradetermform.dev.devplatform.husqvarna-online.net/healthz | jq
```

- Om `buildId` i svar är **lägre** än pipeline build-id → gamla pods svarar, rollout inte klar
- Om `buildId` matchar → nya pods svarar, allt ok

### 2. Jämför build-id

| Källa | Vände |
|------|-------|
| Pipeline: `--build-id 209036` | Förväntat i Ping |
| healthz: `"buildId": "209035"` | Faktiskt deployat (gamla pods) |

### 3. Testa lokalt

```bash
docker build -t tradetermform:test .
docker run --rm -p 4001:4001 \
  -e BUILD_ID=209036 \
  -e BUILD_NUMBER="20260312.4" \
  -e SOURCE_VERSION=$(git rev-parse HEAD) \
  tradetermform:test
# I annat fönster:
curl http://localhost:4001/healthz | jq
```

## Åtgärder

### A. Kontakta DevPlatform-teamet (rekommenderat)

Be dem:

1. **Vänta på rollout** innan Ping körs, t.ex.:
   ```bash
   kubectl rollout status deployment/<app> -n <namespace> --timeout=120s
   ```

2. **Eller**: Öka delay mellan deploy och Ping (t.ex. 60–90 s) så att nya pods hinner komma in i rotation

3. **Eller**: Säkerställ att `@husqvarna/cli health ping-retry` har tillräckligt många retries med längre intervall (nu ~2 s mellan försök; rollout kan ta 1–2 min)

### B. Kontrollera template-parametrar

Platform-mallen `service/v1/azure-pipelines.yml` kan ha parametrar för health check. Kolla i [platform-pipelines](https://dev.azure.com/HQV-DBP/DevPlatform/_git/platform-pipelines) om det finns t.ex.:

- `healthCheckDelay`
- `rolloutWaitTimeout`
- `pingRetries` / `pingRetryDelay`

och lägg till i `azure-pipelines.yml`:

```yaml
extends:
  template: service/v1/azure-pipelines.yml@pipelines
  parameters:
    domain: tradein
    service: automower-tradetermform
    # Om mallen stöder:
    # healthCheckDelay: 90
    # rolloutWaitTimeout: 120
    scaling: ...
```

### C. Ytterligare deploy (enkel test)

Ibland lyckas nästa deploy p.g.a. slumpmässig timing. Kör en tom commit för att trigga ny pipeline:

```bash
git commit --allow-empty -m "chore: trigger deploy"
git push ado main
```

## Checklista

- [ ] `/healthz` returnerar v2 med `info.buildId`
- [ ] `BUILD_ID` (och andra env vars) sätts av plattformen
- [ ] Docker HEALTHCHECK finns och fungerar
- [ ] Image byggs från rätt commit (kolla i Azure DevOps)
- [ ] Ping körs för tidigt i förhållande till rollout

## Referens: v2 healthz-format

```json
{
  "status": "ok",
  "version": 2,
  "info": {
    "buildId": "<BUILD_ID>",
    "buildNumber": "<BUILD_NUMBER>",
    "sourceVersion": "<SOURCE_VERSION>",
    "serviceInstance": "<SERVICE_INSTANCE>",
    "serviceName": "<SERVICE_NAME>",
    "serviceDomain": "<SERVICE_DOMAIN>",
    "logLevel": "info"
  }
}
```
