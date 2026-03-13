# Deploying Trade-in Form on Husqvarna DevPlatform

This document describes how the **Automower Trade-in Form** app relates to the Husqvarna DevPlatform and what is needed to run it there.

**DevPlatform project:** [Azure DevOps – HQV-DBP/DevPlatform](https://dev.azure.com/HQV-DBP/DevPlatform)

## How this app is built

| Aspect | This app | DevPlatform standard |
|--------|----------|----------------------|
| **Runtime** | Python 3.12 | Node.js |
| **Framework** | FastAPI | Express |
| **API style** | REST (JSON + multipart) | GraphQL (Apollo Federation subgraph) |
| **Data** | SQLite (single file) | PostgreSQL + Redis |
| **Deployment** | Single Docker container, **port 4001** | Containers on OpenShift |

The app is a **single service**: one process serves the HTML form, static assets, and REST API. It does not implement a GraphQL subgraph.

## Can it run on the DevPlatform?

The DevPlatform doc states:

- **Containers:** All services are deployed as containers on **Husqvarna OpenShift Kubernetes**.
- **Flexibility:** *"Teams have the freedom to choose alternative technologies if needed."*

So the app **can** run on the platform as a **standalone container**, without using the Node/GraphQL boilerplate. It will not be part of the GraphQL supergraph; it will be one of the "Other Services" behind the Application Gateway.

## What the platform team needs to provide

1. **Container deployment**
   - Build and run the existing Dockerfile (no Node/GraphQL pipeline).
   - Image can be built from this repo; no boilerplate template required.

2. **Configuration (env) – Key Vault secrets**
   - `AUTH_CLIENT_SECRET` – Entra SSO client secret (via Key Vault `|DOMAIN|` placeholder in `config/.env.*`).
   - `AUTH_COOKIE_SECRET` – session signing key (via Key Vault `|DOMAIN|` placeholder).
   - `DB_PATH` – path to SQLite file on the persistent volume (default: `/app/data/tradein.db`).
   - `UPLOADS_DIR` – path for uploaded files on the persistent volume (default: `/app/uploads`).

3. **Persistent storage – CRITICAL**
   Without persistent volumes, all form submissions and uploaded files are **lost on every deploy**.
   Two PVCs are required:

   | Name | Mount path | Suggested size | Contents |
   |------|-----------|----------------|----------|
   | `data` | `/app/data` | 1 Gi | `tradein.db` (SQLite) |
   | `uploads` | `/app/uploads` | 10 Gi | Uploaded images and PDFs |

   These are declared in `azure-pipelines.yml` under `storage:`. Verify the exact parameter
   names with the DevPlatform team against the `service/v1` template version in use.

4. **Routing**
   - Expose the service via Route/Ingress on port **4001**.
   - Admin UI is at `/admin` – access requires Entra SSO login (no separate token needed).

5. **No GraphQL / supergraph**
   - This service is REST-only. No subgraph registration, no GraphQL Hive.

## Summary

- **Yes**, the app can be deployed on the Husqvarna DevPlatform as a **custom container** on OpenShift.
- It does **not** use the standard Node/Express/GraphQL stack; it is Python/FastAPI/REST.
- Admin authentication is **SSO-only** (Entra). No `ADMIN_ACCESS_TOKEN` is used.
- Requirements: run the existing Docker image, inject Key Vault secrets from `config/.env.*`,
  provide persistent volumes for DB and uploads, and route port **4001**.

For questions, align with the Platform Team (DevPlatform/platform-pipelines).
