# GitHub Copilot Instructions for `hsq-tradetermform`

This repository is a **Streamlit data analytics app** that integrates **Databricks**, **Clarity**, and **Azure OpenAI**.

These instructions tell GitHub Copilot (and other AI agents) how to work in this project.

## General

- Prefer **concise, production-quality code** with clear structure.
- Keep **code, comments, and UI text in English**, unless Swedish is explicitly requested.

## Config-first workflow

When adding or changing functionality:

- **Interfaces**: add or update interface definitions in `config/interfaces_config.py` first.
- **KPIs**: add or update KPI definitions in `config/kpis_config.py`.
- **Schemas**: maintain schema and column descriptions in `config/schema_descriptions.py`.
- Only after config is in place, **wire it into Streamlit views, Databricks queries, and charts**.

## Use existing utilities (do not duplicate)

When implementing new features:

- Reuse the project’s existing helpers for:
  - **Databricks access**
  - **Charts/visualizations**
  - **LLM / Azure OpenAI calls**
  - **Clarity API integration**
  - **Layout and styling**
- **Do not duplicate** logic that already exists in these utility modules; extend or wrap them instead.

## Databricks conventions

- Always use **fully-qualified table names**: `catalog.schema.table`.
- For B2B analytics, prefer these tables when relevant:
  - `b2b_gold_salesmanagement_orders_enriched`
  - `b2b_gold_salesmanagement_customer_summary`
- Keep query logic **modular and reusable**, and avoid embedding large SQL strings directly in UI components when a shared helper can be used.

## AI behavior in this repo

- Treat these instructions as **authoritative** for AI-generated code in this repository.
- Align suggestions with the existing **Streamlit + Databricks + Azure OpenAI** architecture.
- Avoid introducing new foundational patterns unless necessary; prefer **extending existing configs and utilities**.

