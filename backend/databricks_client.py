"""
Databricks integration: Delta table sync and Unity Catalog Volume file storage.

All SQL goes via the Databricks SQL Statement Execution REST API (no extra driver needed).
Files go via the Files REST API to the Unity Catalog Volume.
"""

import asyncio
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_CATALOG = "marketing_insight_prod"
_SCHEMA = "nextgenb2b"
_VOLUME = "uploads-tradeterms"

def _is_dev() -> bool:
    return os.getenv("ENVIRONMENT", "dev") == "dev"

def _submissions_table() -> str:
    return f"{_CATALOG}.{_SCHEMA}.b2b_tradeterms_submissions_dev" if _is_dev() else f"{_CATALOG}.{_SCHEMA}.b2b_tradeterms_submissions"

def _products_table() -> str:
    return f"{_CATALOG}.{_SCHEMA}.b2b_tradeterms_products_dev" if _is_dev() else f"{_CATALOG}.{_SCHEMA}.b2b_tradeterms_products"

def _volume_prefix() -> str:
    return "dev/" if _is_dev() else ""


def _host() -> str:
    return os.getenv("DATABRICKS_HOST", "").rstrip("/")


def _token() -> str:
    return os.getenv("DATABRICKSTOKEN", "")


def _warehouse_id() -> str:
    return os.getenv("DATABRICKS_WAREHOUSE_ID", "")


def is_configured() -> bool:
    return bool(_host() and _token() and _warehouse_id())


def _auth_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {_token()}"}


async def _run_sql(
    statement: str,
    parameters: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Execute SQL and wait for result, polling if needed."""
    body: Dict[str, Any] = {
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
            headers=_auth_headers(),
            json=body,
        )
        resp.raise_for_status()
        result = resp.json()

    statement_id = result.get("statement_id")
    state = result.get("status", {}).get("state", "")

    # Poll if still running
    while state in ("RUNNING", "PENDING") and statement_id:
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{_host()}/api/2.0/sql/statements/{statement_id}",
                headers=_auth_headers(),
            )
            resp.raise_for_status()
            result = resp.json()
        state = result.get("status", {}).get("state", "")

    if state == "FAILED":
        error = result.get("status", {}).get("error", {})
        raise RuntimeError(f"Databricks SQL failed: {error.get('message', state)}")

    return result


async def ensure_tables() -> None:
    """Create Delta tables if they don't exist. Called at app startup."""
    if not is_configured():
        logger.info("Databricks not configured – skipping table init")
        return

    stmts = [
        f"""CREATE TABLE IF NOT EXISTS {_submissions_table()} (
            id         BIGINT    NOT NULL,
            submitted_at TIMESTAMP NOT NULL,
            language   STRING,
            dealer_no  STRING,
            company_name STRING,
            postal_location STRING,
            email      STRING,
            synced_at  TIMESTAMP NOT NULL
        ) USING DELTA""",
        f"""CREATE TABLE IF NOT EXISTS {_products_table()} (
            id                          BIGINT NOT NULL,
            submission_id               BIGINT NOT NULL,
            product_index               INT,
            sold_model                  STRING,
            new_serial_number           STRING,
            trade_in_type               STRING,
            trade_in_serial_number      STRING,
            trade_in_nameplate_path     STRING,
            trade_in_product_image_path STRING,
            invoice_path                STRING
        ) USING DELTA""",
    ]
    for stmt in stmts:
        try:
            await _run_sql(stmt)
            logger.info("Databricks table ensured: %s", stmt.split("EXISTS")[-1].split("(")[0].strip())
        except Exception as exc:
            logger.error("ensure_tables failed: %s", exc)


# ---------------------------------------------------------------------------
# File operations (Unity Catalog Volumes)
# ---------------------------------------------------------------------------

def _volume_url(filename: str) -> str:
    return f"{_host()}/api/2.0/fs/files/Volumes/{_CATALOG}/{_SCHEMA}/{_VOLUME}/{_volume_prefix()}{filename}"


async def upload_file(content: bytes, filename: str) -> str:
    """Upload to Unity Catalog Volume. Returns volume-relative path."""
    if not is_configured():
        return ""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.put(
            _volume_url(filename),
            headers={**_auth_headers(), "Content-Type": "application/octet-stream"},
            content=content,
        )
        resp.raise_for_status()
    return f"{_VOLUME}/{_volume_prefix()}{filename}"


async def download_file(volume_relative_path: str) -> tuple[bytes, str]:
    """Download from Unity Catalog Volume. Returns (content, content_type)."""
    url = f"{_host()}/api/2.0/fs/files/Volumes/{_CATALOG}/{_SCHEMA}/{volume_relative_path}"
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url, headers=_auth_headers())
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "application/octet-stream")
        # Derive from filename if generic
        if content_type == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(volume_relative_path)
            if guessed:
                content_type = guessed
        return resp.content, content_type


# ---------------------------------------------------------------------------
# Sync submission (background task)
# ---------------------------------------------------------------------------

async def sync_submission(
    *,
    submission_id: int,
    submitted_at: str,
    language: str,
    dealer: Dict[str, Any],
    products: List[Dict[str, Any]],
    uploads_dir: Path,
) -> bool:
    """
    Background task: upload files to Databricks Volume and insert rows into Delta tables.
    `products` are dicts with keys matching the SQLite products schema.
    """
    if not is_configured():
        logger.info("Databricks not configured – skipping sync for submission %d", submission_id)
        return False

    from datetime import datetime, timezone
    synced_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    # Upload each file to Volume, replace local path with Databricks path
    for prod in products:
        for path_key in (
            "trade_in_nameplate_path",
            "trade_in_product_image_path",
            "invoice_path",
        ):
            local_rel = prod.get(path_key)  # e.g. "uploads/123_0_key.jpg"
            if not local_rel:
                continue
            local_file = uploads_dir.parent / local_rel
            if not local_file.exists():
                logger.warning("Local file not found for upload: %s", local_file)
                continue
            try:
                db_path = await upload_file(local_file.read_bytes(), local_file.name)
                prod[path_key] = db_path  # e.g. "uploads-tradeterms/123_0_key.jpg"
            except Exception as exc:
                logger.error("Volume upload failed (%s): %s", local_rel, exc)

    # Upsert submission row (MERGE ensures idempotency on retry)
    try:
        await _run_sql(
            f"""MERGE INTO {_submissions_table()} AS t
                USING (SELECT
                    CAST(:id AS BIGINT)            AS id,
                    TO_TIMESTAMP(:submitted_at)    AS submitted_at,
                    :language                      AS language,
                    :dealer_no                     AS dealer_no,
                    :company_name                  AS company_name,
                    :postal_location               AS postal_location,
                    :email                         AS email,
                    TO_TIMESTAMP(:synced_at)       AS synced_at
                ) AS s ON t.id = s.id
                WHEN NOT MATCHED THEN INSERT
                    (id, submitted_at, language, dealer_no, company_name, postal_location, email, synced_at)
                    VALUES (s.id, s.submitted_at, s.language, s.dealer_no, s.company_name,
                            s.postal_location, s.email, s.synced_at)""",
            parameters=[
                {"name": "id",              "value": str(submission_id), "type": "LONG"},
                {"name": "submitted_at",    "value": submitted_at,       "type": "STRING"},
                {"name": "language",        "value": language,           "type": "STRING"},
                {"name": "dealer_no",       "value": dealer.get("dealerNo", ""),       "type": "STRING"},
                {"name": "company_name",    "value": dealer.get("companyName", ""),    "type": "STRING"},
                {"name": "postal_location", "value": dealer.get("postalLocation", ""), "type": "STRING"},
                {"name": "email",           "value": dealer.get("email", ""),          "type": "STRING"},
                {"name": "synced_at",       "value": synced_at,          "type": "STRING"},
            ],
        )
    except Exception as exc:
        logger.error("Failed to upsert submission %d into Databricks: %s", submission_id, exc)
        return False

    # Upsert product rows
    all_products_ok = True
    for prod in products:
        try:
            await _run_sql(
                f"""MERGE INTO {_products_table()} AS t
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
                    {"name": "submission_id",               "value": str(submission_id),                             "type": "LONG"},
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
            logger.error("Failed to upsert product %s into Databricks: %s", prod.get("id"), exc)
            all_products_ok = False

    if all_products_ok:
        logger.info("Synced submission %d to Databricks (%d products)", submission_id, len(products))
    else:
        logger.warning(
            "Submission %d synced to Databricks but some products failed", submission_id
        )
    return all_products_ok


# ---------------------------------------------------------------------------
# Admin reads
# ---------------------------------------------------------------------------

def _parse_rows(result: Dict[str, Any]) -> tuple[List[str], List[List]]:
    columns = [
        c["name"]
        for c in result.get("manifest", {}).get("schema", {}).get("columns", [])
    ]
    rows = result.get("result", {}).get("data_array", [])
    return columns, rows


async def fetch_submissions(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetch submissions with their products from Databricks, grouped by submission."""
    result = await _run_sql(
        f"""
        SELECT
            s.id, s.submitted_at, s.language,
            s.dealer_no, s.company_name, s.postal_location, s.email,
            p.id            AS product_id,
            p.product_index,
            p.sold_model,
            p.new_serial_number,
            p.trade_in_type,
            p.trade_in_serial_number,
            p.trade_in_nameplate_path,
            p.trade_in_product_image_path,
            p.invoice_path
        FROM {_submissions_table()} s
        LEFT JOIN {_products_table()} p ON p.submission_id = s.id
        ORDER BY s.submitted_at DESC, s.id DESC, p.product_index ASC
        LIMIT {int(limit)} OFFSET {int(offset)}
        """
    )
    columns, rows = _parse_rows(result)

    submissions: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        r = dict(zip(columns, row))
        sid = int(r["id"])
        if sid not in submissions:
            submissions[sid] = {
                "id": sid,
                "submitted_at": str(r.get("submitted_at") or ""),
                "language": r.get("language") or "",
                "dealer": {
                    "dealerNo":       r.get("dealer_no") or "",
                    "companyName":    r.get("company_name") or "",
                    "postalLocation": r.get("postal_location") or "",
                    "email":          r.get("email") or "",
                },
                "products": [],
            }
        if r.get("product_id") is not None:
            submissions[sid]["products"].append({
                "id":                     int(r["product_id"]),
                "productIndex":           int(r.get("product_index") or 0),
                "soldModel":              r.get("sold_model"),
                "newSerialNumber":        r.get("new_serial_number"),
                "tradeInType":            r.get("trade_in_type"),
                "tradeInSerialNumber":    r.get("trade_in_serial_number"),
                "tradeInNameplatePath":   r.get("trade_in_nameplate_path") or None,
                "tradeInProductImagePath": r.get("trade_in_product_image_path") or None,
                "invoicePath":            r.get("invoice_path") or None,
            })

    return list(submissions.values())
