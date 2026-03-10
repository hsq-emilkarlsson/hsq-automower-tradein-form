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

2. **Configuration (env)**
   - `ADMIN_ACCESS_TOKEN` – from **Azure Key Vault** (or platform secrets), not in code.
   - `DB_PATH` – path where SQLite file is stored (must be on persistent volume).
   - `UPLOADS_DIR` – path for uploaded files (must be on persistent volume).

3. **Persistent storage**
   - Two writable directories that survive pod restarts:
     - Database: `DB_PATH` (e.g. `/data`) for `tradein.db`.
     - Files: `UPLOADS_DIR` (e.g. `/uploads`) for attachments.
   - Implemented via OpenShift persistent volumes (e.g. PVCs) mounted into the container.

4. **Routing**
   - Expose the service (e.g. via Route/Ingress) and route a path (e.g. `/tradein` or a dedicated hostname) to this container on port **4001** (platform requirement).

5. **No GraphQL / supergraph**
   - This service is REST-only. No subgraph registration, no GraphQL Hive.

## Summary

- **Yes**, the app can be deployed on the Husqvarna DevPlatform as a **custom container** on OpenShift.
- It does **not** use the standard Node/Express/GraphQL stack; it is Python/FastAPI/REST.
- Requirements: run the existing Docker image, inject env (especially `ADMIN_ACCESS_TOKEN`) from Key Vault, and provide persistent volumes for DB and uploads plus routing to port **4001**.

For questions, the app owner can align with the Platform Team (see [Contact Information](https://github.com/hsq-emilkarlsson/hsq-automower-tradein-form) in the DevPlatform doc).
