import json
import os
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

from .db import fetch_submissions, init_db, insert_submission

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", str(BASE_DIR / "uploads")))
ADMIN_ACCESS_TOKEN = os.getenv("ADMIN_ACCESS_TOKEN", "")
AUTH_CLIENT_ID = os.getenv("AUTH_CLIENT_ID", "")
AUTH_CLIENT_SECRET = os.getenv("AUTH_CLIENT_SECRET", "")
AUTH_REDIRECT_URI = os.getenv("AUTH_REDIRECT_URI", "")
AUTH_COOKIE_SECRET = os.getenv("AUTH_COOKIE_SECRET", "")
AUTH_SERVER_METADATA_URL = os.getenv("AUTH_SERVER_METADATA_URL", "")


def _ensure_dirs() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="Automower Trade-in Backend")

# Session middleware for SSO (used regardless of whether SSO is configured, harmless otherwise)
session_secret = AUTH_COOKIE_SECRET or "change-me-session-secret-for-production"
app.add_middleware(SessionMiddleware, secret_key=session_secret, same_site="lax", https_only=False)

oauth: Optional[OAuth] = None

def _is_sso_configured() -> bool:
    return bool(AUTH_CLIENT_ID and AUTH_CLIENT_SECRET and AUTH_SERVER_METADATA_URL)

if _is_sso_configured():
    oauth = OAuth()
    oauth.register(
        name="entra",
        client_id=AUTH_CLIENT_ID,
        client_secret=AUTH_CLIENT_SECRET,
        server_metadata_url=AUTH_SERVER_METADATA_URL,
        client_kwargs={"scope": "openid email profile"},
    )


@app.on_event("startup")
def on_startup() -> None:
    _ensure_dirs()
    init_db()


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Health check endpoint for DevPlatform pipeline."""
    return JSONResponse({"status": "ok"})


def _build_public_base_url(request: Request) -> str:
    """
    Resolve the public base URL used when building absolute links.

    - Prefer PUBLIC_BASE_URL env var (for production behind proxies)
    - Fall back to request.base_url (dev/local usage)
    """
    public_base_url = os.getenv("PUBLIC_BASE_URL")
    if public_base_url:
        return public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _build_file_url(path: Optional[str], request: Request) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base_url = _build_public_base_url(request)
    return f"{base_url}/{path.lstrip('/')}"


async def notify_n8n_new_submission(submission_id: int, payload: Dict[str, Any]) -> None:
    """
    Optionally notify an n8n webhook when a new submission is created.

    Controlled by the N8N_WEBHOOK_URL environment variable.
    Failures are logged to stderr but do not affect the main flow.
    """
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                webhook_url,
                json={
                    "submissionId": submission_id,
                    "payload": payload,
                },
            )
    except Exception:
        # In production you might want to plug in proper logging here.
        return


def _is_admin_request(request: Request) -> bool:
    """
    Check whether the incoming request is authorized for admin access.

    - Accepts SSO session:
      - request.session[\"user\"] set by Entra login
    - Accepts ADMIN_ACCESS_TOKEN for programmatic/API access via:
      - X-Admin-Token header (for API clients like Databricks)
      - admin_token cookie (for browser-based admin UI)
      - optional token/admin_token query parameter (fallback for browsers)
    """
    # First, trust a valid SSO session set by Entra login.
    user = request.session.get("user") if hasattr(request, "session") else None
    if user and isinstance(user, dict) and user.get("email"):
        return True

    # Backwards-compatible token-based admin access for API clients.
    # When SSO is configured, we only honor tokens from the X-Admin-Token header
    # (for Databricks/n8n etc.), not cookies/query-params from browsers.
    if not ADMIN_ACCESS_TOKEN:
        # If no token is configured, treat as locked down (no implicit token access).
        return False

    header_token = request.headers.get("X-Admin-Token")
    cookie_token = request.cookies.get("admin_token")
    query_token = request.query_params.get("token") or request.query_params.get("admin_token")

    # If SSO is configured, ignore browser cookies/query tokens and only accept headers.
    if oauth is not None:
        token = header_token
    else:
        token = header_token or cookie_token or query_token

    if not token:
        return False

    return secrets.compare_digest(token, ADMIN_ACCESS_TOKEN)


def get_current_admin(request: Request) -> str:
    """Dependency that enforces admin access using the access token."""
    if not _is_admin_request(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    return "admin"


app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR), html=False),
    name="static",
)
app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOADS_DIR), html=False),
    name="uploads",
)


@app.get("/")
async def index() -> FileResponse:
    """Serve the main form."""
    index_path = BASE_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index_path))


@app.get("/admin-login")
async def admin_login_page(request: Request) -> Response:
    """
    Start the SSO login flow for admin access.

    - If Entra SSO is configured, redirect to Microsoft login.
    - If not configured, fall back to the legacy token login page.
    """
    if oauth is not None:
        # Compute redirect URI: either from env or from current request.
        redirect_uri = AUTH_REDIRECT_URI or str(request.url_for("auth_callback"))
        return await oauth.entra.authorize_redirect(request, redirect_uri)

    # Fallback: legacy token-based login page
    login_path = BASE_DIR / "admin-login.html"
    if not login_path.exists():
        raise HTTPException(status_code=404, detail="admin-login.html not found")
    return FileResponse(str(login_path))


@app.get("/admin")
async def admin_page(request: Request) -> FileResponse:
    """
    Serve the admin UI.

    If the request is not authorized, redirect to login instead.
    """
    if not _is_admin_request(request):
        # Prefer SSO login when configured
        if oauth is not None:
            return RedirectResponse(url="/admin-login")

        # Fallback: legacy token-based login page
        login_path = BASE_DIR / "admin-login.html"
        if not login_path.exists():
            raise HTTPException(status_code=404, detail="admin-login.html not found")
        return FileResponse(str(login_path))

    admin_path = BASE_DIR / "admin.html"
    if not admin_path.exists():
        raise HTTPException(status_code=404, detail="admin.html not found")
    return FileResponse(str(admin_path))


@app.get("/oauth2callback", name="auth_callback")
async def auth_callback(request: Request) -> Response:
    """
    Handle the OAuth2 callback from Microsoft Entra and establish an admin session.
    """
    if oauth is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SSO is not configured.",
        )

    token = await oauth.entra.authorize_access_token(request)
    # Try to get userinfo from the provider; fall back to ID token claims.
    userinfo: Dict[str, Any] = token.get("userinfo") or {}
    if not userinfo:
        userinfo = token.get("id_token_claims", {})

    email = userinfo.get("email") or userinfo.get("preferred_username")
    name = userinfo.get("name") or email or "Admin"

    request.session["user"] = {
        "email": email,
        "name": name,
        "sub": userinfo.get("sub"),
    }

    return RedirectResponse(url="/admin")


@app.get("/admin/logout")
async def admin_sso_logout(request: Request) -> Response:
    """
    Clear the SSO admin session and redirect to the public form.
    """
    request.session.pop("user", None)
    return RedirectResponse(url="/")


@app.post("/api/admin/login")
async def admin_login(request: Request, token: str = Form(..., alias="token")) -> JSONResponse:
    """
    Validate an access token and issue an HTTP-only cookie for admin access.
    """
    if not ADMIN_ACCESS_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin access token is not configured.",
        )

    token = (token or "").strip()
    if not secrets.compare_digest(token, ADMIN_ACCESS_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    response = JSONResponse({"success": True})
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response


@app.post("/api/admin/logout")
async def admin_logout() -> JSONResponse:
    """Clear the admin cookie."""
    response = JSONResponse({"success": True})
    response.delete_cookie("admin_token")
    return response


def _save_upload_file(
    key: str,
    upload,
    submission_id: int,
    product_index: int,
) -> str:
    """Persist an uploaded file and return its relative path."""
    if not upload or not getattr(upload, "filename", None):
        return ""

    suffix = Path(upload.filename).suffix or ""
    safe_key = key.replace("[", "_").replace("]", "_")
    filename = f"{submission_id}_{product_index}_{safe_key}{suffix}"
    destination = UPLOADS_DIR / filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    # Store path relative to project root so it can be turned into a URL easily.
    return f"uploads/{filename}"


@app.post("/api/submissions")
async def create_submission(request: Request) -> JSONResponse:
    """
    Accept form submissions from the frontend.

    Expects multipart/form-data with:
      - payload: JSON string containing dealer + product info
      - file fields as constructed in script.js
    """
    form = await request.form()

    payload_raw = form.get("payload")
    if not payload_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing payload field",
        )

    try:
        payload: Dict[str, Any] = json.loads(payload_raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON in payload field",
        )

    language = payload.get("language") or "en"
    dealer = payload.get("dealer") or {}
    base_product = payload.get("product") or {}
    additional_products = payload.get("additionalProducts") or []

    submitted_at = payload.get("submittedAt") or datetime.now(tz=timezone.utc).isoformat()

    # Collect all file-like objects from the form.
    file_objects: Dict[str, Any] = {}
    for key, value in form.multi_items():
        if hasattr(value, "filename") and value.filename:
            file_objects[key] = value

    # Insert a preliminary submission to obtain an ID.
    # Files will be saved and the same ID used for product rows.
    # We first build product structures with file paths, then call insert_submission.
    all_products: List[Dict[str, Any]] = []

    def build_product(
        product: Dict[str, Any],
        product_index: int,
    ) -> Dict[str, Any]:
        trade_in_serial_number = product.get("tradeInSerialNumber") or ""
        trade_in_nameplate_key = product.get("tradeInNameplateKey")
        trade_in_product_image_key = product.get("tradeInProductImageKey")
        invoice_key = product.get("invoiceKey")

        return {
            "product_index": product_index,
            "sold_model": product.get("soldModel") or product.get("sold_model") or "",
            "new_serial_number": product.get("newSerialNumber")
            or product.get("new_serial_number")
            or "",
            "trade_in_type": product.get("tradeInType")
            or product.get("trade_in_type")
            or "",
            "trade_in_serial_number": trade_in_serial_number or None,
            # File paths are filled after we know the submission id.
            "trade_in_nameplate_key": trade_in_nameplate_key,
            "trade_in_product_image_key": trade_in_product_image_key,
            "invoice_key": invoice_key,
            "trade_in_nameplate_path": None,
            "trade_in_product_image_path": None,
            "invoice_path": None,
        }

    all_products.append(build_product(base_product, 0))
    for idx, prod in enumerate(additional_products, start=1):
        all_products.append(build_product(prod, idx))

    # Temporarily insert without file paths, then update with saved paths.
    # We perform a single logical operation: save submission and products.
    # Files are saved based on the generated submission_id.
    submission_id = insert_submission(
        submitted_at=submitted_at,
        language=language,
        dealer=dealer,
        products=[
            {
                "product_index": p["product_index"],
                "sold_model": p["sold_model"],
                "new_serial_number": p["new_serial_number"],
                "trade_in_type": p["trade_in_type"],
                "trade_in_serial_number": p.get("trade_in_serial_number"),
                "trade_in_nameplate_path": None,
                "trade_in_product_image_path": None,
                "invoice_path": None,
            }
            for p in all_products
        ],
    )

    # Now save files and patch paths in the database using direct SQL.
    # This keeps responsibilities separated: db.py knows about schema, and this
    # module knows how files map to products.
    from .db import get_connection  # local import to avoid circular

    from_db_products = []
    conn = get_connection()
    try:
        cursor = conn.cursor()
        rows = cursor.execute(
            """
            SELECT id, product_index
            FROM products
            WHERE submission_id = ?
            ORDER BY product_index ASC, id ASC
            """,
            (submission_id,),
        ).fetchall()

        for row in rows:
            from_db_products.append({"db_id": row["id"], "product_index": row["product_index"]})

        for prod in all_products:
            matching = next(
                (p for p in from_db_products if p["product_index"] == prod["product_index"]),
                None,
            )
            if not matching:
                continue

            db_id = matching["db_id"]
            nameplate_path = ""
            product_image_path = ""
            invoice_path = ""

            if prod.get("trade_in_nameplate_key"):
                upload = file_objects.get(prod["trade_in_nameplate_key"])
                if upload:
                    nameplate_path = _save_upload_file(
                        prod["trade_in_nameplate_key"],
                        upload,
                        submission_id,
                        prod["product_index"],
                    )
            if prod.get("trade_in_product_image_key"):
                upload = file_objects.get(prod["trade_in_product_image_key"])
                if upload:
                    product_image_path = _save_upload_file(
                        prod["trade_in_product_image_key"],
                        upload,
                        submission_id,
                        prod["product_index"],
                    )
            if prod.get("invoice_key"):
                upload = file_objects.get(prod["invoice_key"])
                if upload:
                    invoice_path = _save_upload_file(
                        prod["invoice_key"],
                        upload,
                        submission_id,
                        prod["product_index"],
                    )

            cursor.execute(
                """
                UPDATE products
                SET
                    trade_in_nameplate_path = ?,
                    trade_in_product_image_path = ?,
                    invoice_path = ?
                WHERE id = ?
                """,
                (nameplate_path or None, product_image_path or None, invoice_path or None, db_id),
            )

        conn.commit()
    finally:
        conn.close()

    # Fire-and-forget n8n notification with the original payload.
    await notify_n8n_new_submission(submission_id, payload)

    return JSONResponse({"id": submission_id, "success": True})


@app.get("/api/submissions")
async def list_submissions(
    limit: int = Query(100, ge=1, le=10_000),
    offset: int = Query(0, ge=0),
    current_admin: str = Depends(get_current_admin),
) -> JSONResponse:
    """
    Return submissions with nested products.

    This endpoint is primarily intended for admin usage.
    """
    submissions = fetch_submissions(limit=limit, offset=offset)
    return JSONResponse(submissions)


@app.get("/api/submissions/flat")
async def list_submissions_flat(
    request: Request,
    limit: int = Query(1000, ge=1, le=10_000),
    offset: int = Query(0, ge=0),
    from_date: Optional[str] = Query(
        None,
        description="ISO 8601 start datetime filter on submittedAt (inclusive)",
    ),
    to_date: Optional[str] = Query(
        None,
        description="ISO 8601 end datetime filter on submittedAt (inclusive)",
    ),
    current_admin: str = Depends(get_current_admin),
) -> JSONResponse:
    """
    Return a flat list of product rows, convenient for analytics / Databricks.

    Each item corresponds to one product on a submission and includes
    dealer info and absolute URLs to uploaded files.
    """
    submissions = fetch_submissions(limit=limit, offset=offset)

    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    if from_date:
        from_dt = datetime.fromisoformat(from_date)
    if to_date:
        to_dt = datetime.fromisoformat(to_date)

    rows: List[Dict[str, Any]] = []
    for sub in submissions:
        submitted_at_str = sub["submitted_at"]
        try:
            submitted_at = datetime.fromisoformat(submitted_at_str)
        except Exception:
            submitted_at = None

        if submitted_at and from_dt and submitted_at < from_dt:
            continue
        if submitted_at and to_dt and submitted_at > to_dt:
            continue

        for product in sub["products"]:
            rows.append(
                {
                    "submissionId": sub["id"],
                    "submittedAt": submitted_at_str,
                    "language": sub["language"],
                    "dealerNo": sub["dealer"]["dealerNo"],
                    "companyName": sub["dealer"]["companyName"],
                    "postalLocation": sub["dealer"]["postalLocation"],
                    "email": sub["dealer"]["email"],
                    "productIndex": product["productIndex"],
                    "soldModel": product["soldModel"],
                    "newSerialNumber": product["newSerialNumber"],
                    "tradeInType": product["tradeInType"],
                    "tradeInSerialNumber": product["tradeInSerialNumber"],
                    "tradeInNameplateUrl": _build_file_url(
                        product.get("tradeInNameplatePath"), request
                    ),
                    "tradeInProductImageUrl": _build_file_url(
                        product.get("tradeInProductImagePath"), request
                    ),
                    "invoiceUrl": _build_file_url(product.get("invoicePath"), request),
                }
            )

    return JSONResponse(rows)


@app.get("/api/submissions/export")
async def export_submissions(
    request: Request,
    current_admin: str = Depends(get_current_admin),
) -> Response:
    """
    Export all submissions as an Excel file (one row per product),
    with hyperlinks to uploaded files.
    """
    from io import BytesIO

    from openpyxl import Workbook

    submissions = fetch_submissions(limit=10_000, offset=0)

    # Determine base URL for hyperlinks:
    # - Prefer PUBLIC_BASE_URL env var (for prod)
    # - Fallback to the current request base URL (for dev, e.g. http://localhost:8080)
    public_base_url = os.getenv("PUBLIC_BASE_URL")
    if public_base_url:
        base_url = public_base_url.rstrip("/")
    else:
        base_url = str(request.base_url).rstrip("/")

    def build_url(path: str | None) -> str | None:
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{base_url}/{path.lstrip('/')}"

    wb = Workbook()
    ws = wb.active
    ws.title = "Submissions"

    headers = [
        "submissionId",
        "submittedAt",
        "language",
        "dealerNo",
        "companyName",
        "postalLocation",
        "email",
        "productIndex",
        "soldModel",
        "newSerialNumber",
        "tradeInType",
        "tradeInSerialNumber",
        "tradeInNameplateLink",
        "tradeInProductImageLink",
        "invoiceLink",
    ]
    ws.append(headers)

    # Column indices (1-based) for hyperlink columns
    nameplate_col = headers.index("tradeInNameplateLink") + 1
    product_image_col = headers.index("tradeInProductImageLink") + 1
    invoice_col = headers.index("invoiceLink") + 1

    for sub in submissions:
        for product in sub["products"]:
            row_values = [
                sub["id"],
                sub["submitted_at"],
                sub["language"],
                sub["dealer"]["dealerNo"],
                sub["dealer"]["companyName"],
                sub["dealer"]["postalLocation"],
                sub["dealer"]["email"],
                product["productIndex"],
                product["soldModel"],
                product["newSerialNumber"],
                product["tradeInType"],
                product["tradeInSerialNumber"],
                "",  # nameplate link placeholder
                "",  # product image link placeholder
                "",  # invoice link placeholder
            ]
            ws.append(row_values)
            row_idx = ws.max_row

            nameplate_url = build_url(product.get("tradeInNameplatePath"))
            if nameplate_url:
                cell = ws.cell(row=row_idx, column=nameplate_col)
                cell.value = "Nameplate"
                cell.hyperlink = nameplate_url
                cell.style = "Hyperlink"

            product_url = build_url(product.get("tradeInProductImagePath"))
            if product_url:
                cell = ws.cell(row=row_idx, column=product_image_col)
                cell.value = "Product image"
                cell.hyperlink = product_url
                cell.style = "Hyperlink"

            invoice_url = build_url(product.get("invoicePath"))
            if invoice_url:
                cell = ws.cell(row=row_idx, column=invoice_col)
                cell.value = "Invoice"
                cell.hyperlink = invoice_url
                cell.style = "Hyperlink"

    # Basic column width adjustments for readability
    for column_cells in ws.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter  # type: ignore[attr-defined]
        for cell in column_cells:
            value = cell.value
            if value is not None:
                max_length = max(max_length, len(str(value)))
        ws.column_dimensions[column_letter].width = min(max_length + 2, 40)

    buffer = BytesIO()
    wb.save(buffer)

    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="tradein_submissions.xlsx"'},
    )


