"""
Grant Databricks permissions to the app token's identity.

Usage:
    ADMIN_TOKEN=dapi... python3 scripts/grant_databricks_permissions.py

ADMIN_TOKEN  – your personal PAT (needs GRANT privilege)
DATABRICKS_TOKEN in .env – the app token that needs permissions
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx

HOST = os.getenv("DATABRICKS_HOST", "").rstrip("/")
APP_TOKEN = os.getenv("DATABRICKS_TOKEN", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "")

_CATALOG = "marketing_insight_prod"
_SCHEMA = "nextgenb2b"
_VOLUME = "uploads-tradeterms"
_SUBMISSIONS = f"{_CATALOG}.{_SCHEMA}.b2b_submissions"
_PRODUCTS = f"{_CATALOG}.{_SCHEMA}.b2b_products"


async def get_token_owner(token: str) -> str:
    """Return the email/username the token belongs to."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{HOST}/api/2.0/preview/scim/v2/Me",
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("userName") or data.get("displayName") or data.get("id", "")


async def run_sql(sql: str, token: str) -> None:
    body = {
        "warehouse_id": WAREHOUSE_ID,
        "statement": sql,
        "wait_timeout": "50s",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{HOST}/api/2.0/sql/statements",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
        )
        resp.raise_for_status()
        result = resp.json()

    state = result.get("status", {}).get("state", "")
    if state == "FAILED":
        error = result.get("status", {}).get("error", {})
        raise RuntimeError(error.get("message", state))


async def main() -> None:
    if not HOST or not APP_TOKEN or not WAREHOUSE_ID:
        print("ERROR: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID must be set in .env")
        sys.exit(1)
    if not ADMIN_TOKEN:
        print("ERROR: Set ADMIN_TOKEN=dapi... before running this script")
        print("  Example: ADMIN_TOKEN=dapi... python3 scripts/grant_databricks_permissions.py")
        sys.exit(1)

    print("Looking up app token identity...")
    app_user = await get_token_owner(APP_TOKEN)
    print(f"App token belongs to: {app_user}")

    grants = [
        f"GRANT READ VOLUME, WRITE VOLUME ON VOLUME {_CATALOG}.{_SCHEMA}.`{_VOLUME}` TO `{app_user}`",
        f"GRANT INSERT, SELECT ON TABLE {_SUBMISSIONS} TO `{app_user}`",
        f"GRANT INSERT, SELECT ON TABLE {_PRODUCTS} TO `{app_user}`",
        f"GRANT INSERT, SELECT ON TABLE {_SUBMISSIONS}_dev TO `{app_user}`",
        f"GRANT INSERT, SELECT ON TABLE {_PRODUCTS}_dev TO `{app_user}`",
    ]

    for sql in grants:
        desc = sql.split("ON")[0].strip()
        try:
            await run_sql(sql, ADMIN_TOKEN)
            print(f"  OK  {desc}")
        except Exception as exc:
            print(f"  ERR {desc}: {exc}")

    print("\nDone. Re-submit a test form to verify file uploads work.")


asyncio.run(main())
