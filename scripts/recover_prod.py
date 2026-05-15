#!/usr/bin/env python3
"""
One-time recovery script: upload all local files to Databricks Volume and
sync all unsynced submissions to Databricks Delta tables.

Usage:
    python scripts/recover_prod.py [--dry-run] [--db PATH] [--zip PATH]

Defaults:
    --db   tradein-prod.db
    --zip  "uploads 1.zip"

Requires DATABRICKS_HOST, DATABRICKSTOKEN, DATABRICKS_WAREHOUSE_ID in .env
(or environment). Runs against PROD tables (ENVIRONMENT=prod).
"""

import argparse
import asyncio
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
os.environ.setdefault("ENVIRONMENT", "prod")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("recover")

# ---------------------------------------------------------------------------
# Databricks constants (mirrors databricks_client.py)
# ---------------------------------------------------------------------------

_CATALOG = "marketing_insight_prod"
_SCHEMA = "salesmanagement"
_VOLUME = "uploads-tradeterms"
_SUBMISSIONS_TABLE = f"{_CATALOG}.{_SCHEMA}.b2b_tradeterms_submissions"
_PRODUCTS_TABLE = f"{_CATALOG}.{_SCHEMA}.b2b_tradeterms_products"


def _host() -> str:
    return os.environ["DATABRICKS_HOST"].rstrip("/")


def _token() -> str:
    return os.environ["DATABRICKSTOKEN"]


def _warehouse_id() -> str:
    return os.environ["DATABRICKS_WAREHOUSE_ID"]


def _auth() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


# ---------------------------------------------------------------------------
# Databricks helpers
# ---------------------------------------------------------------------------

async def _run_sql(statement: str, parameters: list | None = None) -> dict:
    body: dict = {
        "warehouse_id": _warehouse_id(),
        "statement": statement,
        "wait_timeout": "50s",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
    }
    if parameters:
        body["parameters"] = parameters

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{_host()}/api/2.0/sql/statements",
            headers=_auth(),
            json=body,
        )
        resp.raise_for_status()
        result = resp.json()

    sid = result.get("statement_id")
    state = result.get("status", {}).get("state", "")

    while state in ("RUNNING", "PENDING") and sid:
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{_host()}/api/2.0/sql/statements/{sid}",
                headers=_auth(),
            )
            resp.raise_for_status()
            result = resp.json()
        state = result.get("status", {}).get("state", "")

    if state == "FAILED":
        err = result.get("status", {}).get("error", {})
        raise RuntimeError(f"SQL failed: {err.get('message', state)}")

    return result


async def _upload_file(content: bytes, filename: str, dry_run: bool) -> str:
    """Upload bytes to Databricks Volume. Returns volume-relative path."""
    db_path = f"{_VOLUME}/{filename}"
    if dry_run:
        log.info("    [dry-run] would upload → %s", db_path)
        return db_path
    url = f"{_host()}/api/2.0/fs/files/Volumes/{_CATALOG}/{_SCHEMA}/{_VOLUME}/{filename}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.put(
            url,
            headers={**_auth(), "Content-Type": "application/octet-stream"},
            content=content,
        )
        resp.raise_for_status()
    return db_path


# ---------------------------------------------------------------------------
# SQLite helpers
# ---------------------------------------------------------------------------

def load_unsynced(db_path: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        subs = conn.execute(
            """SELECT id, submitted_at, language, dealer_no, company_name,
                      postal_location, email
               FROM submissions
               WHERE databricks_synced = 0
               ORDER BY id ASC"""
        ).fetchall()
        result = []
        for s in subs:
            prods = conn.execute(
                """SELECT id, product_index, sold_model, new_serial_number,
                          trade_in_type, trade_in_serial_number,
                          trade_in_nameplate_path, trade_in_product_image_path,
                          invoice_path
                   FROM products
                   WHERE submission_id = ?
                   ORDER BY product_index ASC, id ASC""",
                (s["id"],),
            ).fetchall()
            result.append({
                "id": s["id"],
                "submitted_at": s["submitted_at"],
                "language": s["language"],
                "dealer_no": s["dealer_no"],
                "company_name": s["company_name"],
                "postal_location": s["postal_location"],
                "email": s["email"],
                "products": [dict(p) for p in prods],
            })
        return result
    finally:
        conn.close()


def mark_synced_and_update_paths(db_path: str, submission_id: int, products: list[dict], dry_run: bool) -> None:
    if dry_run:
        return
    conn = sqlite3.connect(db_path)
    try:
        for p in products:
            conn.execute(
                """UPDATE products
                   SET trade_in_nameplate_path=?,
                       trade_in_product_image_path=?,
                       invoice_path=?
                   WHERE id=?""",
                (
                    p.get("trade_in_nameplate_path"),
                    p.get("trade_in_product_image_path"),
                    p.get("invoice_path"),
                    p["id"],
                ),
            )
        conn.execute(
            "UPDATE submissions SET databricks_synced=1 WHERE id=?",
            (submission_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main recovery logic
# ---------------------------------------------------------------------------

async def recover_submission(sub: dict, uploads_dir: Path, dry_run: bool, db_path: str) -> bool:
    sub_id = sub["id"]
    products = sub["products"]
    synced_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    # 1. Upload files for each product
    for prod in products:
        for key in ("trade_in_nameplate_path", "trade_in_product_image_path", "invoice_path"):
            local_rel = prod.get(key)
            if not local_rel:
                continue
            filename = Path(local_rel).name
            local_file = uploads_dir / filename
            if not local_file.exists():
                log.warning("  sub %d  prod %d  %s → FILE MISSING in zip, skipping", sub_id, prod["id"], filename)
                continue
            try:
                db_path_file = await _upload_file(local_file.read_bytes(), filename, dry_run)
                prod[key] = db_path_file
                log.info("  sub %d  prod %d  %s → %s", sub_id, prod["id"], filename, db_path_file)
            except Exception as exc:
                log.error("  sub %d  prod %d  upload FAILED (%s): %s", sub_id, prod["id"], filename, exc)
                return False

    if dry_run:
        log.info("  [dry-run] would upsert submission %d + %d product(s) to Databricks", sub_id, len(products))
        return True

    # 2. Upsert submission row
    try:
        await _run_sql(
            f"""MERGE INTO {_SUBMISSIONS_TABLE} AS t
                USING (SELECT
                    CAST(:id AS BIGINT)         AS id,
                    TO_TIMESTAMP(:submitted_at) AS submitted_at,
                    :language                   AS language,
                    :dealer_no                  AS dealer_no,
                    :company_name               AS company_name,
                    :postal_location            AS postal_location,
                    :email                      AS email,
                    TO_TIMESTAMP(:synced_at)    AS synced_at
                ) AS s ON t.id = s.id
                WHEN MATCHED THEN UPDATE SET
                    synced_at = s.synced_at
                WHEN NOT MATCHED THEN INSERT
                    (id, submitted_at, language, dealer_no, company_name, postal_location, email, synced_at)
                    VALUES (s.id, s.submitted_at, s.language, s.dealer_no, s.company_name,
                            s.postal_location, s.email, s.synced_at)""",
            parameters=[
                {"name": "id",              "value": str(sub_id),              "type": "LONG"},
                {"name": "submitted_at",    "value": sub["submitted_at"],       "type": "STRING"},
                {"name": "language",        "value": sub["language"],           "type": "STRING"},
                {"name": "dealer_no",       "value": sub["dealer_no"],          "type": "STRING"},
                {"name": "company_name",    "value": sub["company_name"],       "type": "STRING"},
                {"name": "postal_location", "value": sub["postal_location"],    "type": "STRING"},
                {"name": "email",           "value": sub["email"],              "type": "STRING"},
                {"name": "synced_at",       "value": synced_at,                 "type": "STRING"},
            ],
        )
    except Exception as exc:
        log.error("  sub %d  FAILED to upsert submission: %s", sub_id, exc)
        return False

    # 3. Upsert each product row
    for prod in products:
        try:
            await _run_sql(
                f"""MERGE INTO {_PRODUCTS_TABLE} AS t
                    USING (SELECT
                        CAST(:id AS BIGINT)            AS id,
                        CAST(:submission_id AS BIGINT) AS submission_id,
                        CAST(:product_index AS INT)    AS product_index,
                        :sold_model                    AS sold_model,
                        :new_serial_number             AS new_serial_number,
                        :trade_in_type                 AS trade_in_type,
                        :trade_in_serial_number        AS trade_in_serial_number,
                        :trade_in_nameplate_path       AS trade_in_nameplate_path,
                        :trade_in_product_image_path   AS trade_in_product_image_path,
                        :invoice_path                  AS invoice_path
                    ) AS s ON t.id = s.id
                    WHEN MATCHED THEN UPDATE SET
                        trade_in_nameplate_path     = s.trade_in_nameplate_path,
                        trade_in_product_image_path = s.trade_in_product_image_path,
                        invoice_path                = s.invoice_path
                    WHEN NOT MATCHED THEN INSERT
                        (id, submission_id, product_index, sold_model, new_serial_number,
                         trade_in_type, trade_in_serial_number,
                         trade_in_nameplate_path, trade_in_product_image_path, invoice_path)
                        VALUES (s.id, s.submission_id, s.product_index, s.sold_model,
                                s.new_serial_number, s.trade_in_type, s.trade_in_serial_number,
                                s.trade_in_nameplate_path, s.trade_in_product_image_path,
                                s.invoice_path)""",
                parameters=[
                    {"name": "id",                          "value": str(prod["id"]),                                "type": "LONG"},
                    {"name": "submission_id",               "value": str(sub_id),                                    "type": "LONG"},
                    {"name": "product_index",               "value": str(prod.get("product_index", 0)),              "type": "INT"},
                    {"name": "sold_model",                  "value": prod.get("sold_model") or "",                   "type": "STRING"},
                    {"name": "new_serial_number",           "value": prod.get("new_serial_number") or "",            "type": "STRING"},
                    {"name": "trade_in_type",               "value": prod.get("trade_in_type") or "",                "type": "STRING"},
                    {"name": "trade_in_serial_number",      "value": prod.get("trade_in_serial_number") or "",       "type": "STRING"},
                    {"name": "trade_in_nameplate_path",     "value": prod.get("trade_in_nameplate_path") or "",      "type": "STRING"},
                    {"name": "trade_in_product_image_path", "value": prod.get("trade_in_product_image_path") or "",  "type": "STRING"},
                    {"name": "invoice_path",                "value": prod.get("invoice_path") or "",                 "type": "STRING"},
                ],
            )
        except Exception as exc:
            log.error("  sub %d  prod %d  FAILED to upsert product: %s", sub_id, prod["id"], exc)
            return False

    # 4. Mark as synced in SQLite and update paths
    mark_synced_and_update_paths(db_path, sub_id, products, dry_run=False)
    return True


async def main(db_path: str, zip_path: str, dry_run: bool) -> None:
    # Validate credentials
    missing = [v for v in ("DATABRICKS_HOST", "DATABRICKSTOKEN", "DATABRICKS_WAREHOUSE_ID") if not os.environ.get(v)]
    if missing:
        log.error("Missing env vars: %s", ", ".join(missing))
        sys.exit(1)

    log.info("=== Trade-term prod recovery%s ===", " [DRY RUN]" if dry_run else "")
    log.info("DB:  %s", db_path)
    log.info("Zip: %s", zip_path)
    log.info("Databricks host: %s", _host())

    # Load unsynced submissions
    submissions = load_unsynced(db_path)
    log.info("Unsynced submissions to process: %d", len(submissions))
    if not submissions:
        log.info("Nothing to do.")
        return

    # Extract zip to temp dir
    tmp = tempfile.mkdtemp(prefix="tradeterms_recovery_")
    try:
        log.info("Extracting zip to %s ...", tmp)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        uploads_dir = Path(tmp) / "uploads"
        if not uploads_dir.exists():
            log.error("Expected 'uploads/' folder inside zip, not found")
            sys.exit(1)
        log.info("Extracted %d files", len(list(uploads_dir.iterdir())))

        # Process each submission
        ok = 0
        failed = 0
        for sub in submissions:
            log.info("Processing submission %d (%s) ...", sub["id"], sub["submitted_at"])
            success = await recover_submission(sub, uploads_dir, dry_run, db_path)
            if success:
                ok += 1
                log.info("  ✓ submission %d done", sub["id"])
            else:
                failed += 1
                log.error("  ✗ submission %d FAILED", sub["id"])

        log.info("")
        log.info("=== Done: %d succeeded, %d failed ===", ok, failed)
        if dry_run:
            log.info("This was a dry run — nothing was written to Databricks or SQLite.")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing anything")
    parser.add_argument("--db",  default="tradein-prod.db", help="Path to SQLite DB (default: tradein-prod.db)")
    parser.add_argument("--zip", default="uploads 1.zip",   help="Path to uploads zip (default: 'uploads 1.zip')")
    args = parser.parse_args()

    asyncio.run(main(db_path=args.db, zip_path=args.zip, dry_run=args.dry_run))
