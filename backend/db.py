import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


DB_PATH = os.getenv("DB_PATH", "data/tradein.db")


def _ensure_directories() -> None:
    db_file = Path(DB_PATH)
    if not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with sensible defaults."""
    _ensure_directories()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create tables if they do not exist."""
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submitted_at TEXT NOT NULL,
                language TEXT NOT NULL,
                dealer_no TEXT NOT NULL,
                company_name TEXT NOT NULL,
                postal_location TEXT NOT NULL,
                email TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER NOT NULL,
                product_index INTEGER NOT NULL,
                sold_model TEXT NOT NULL,
                new_serial_number TEXT NOT NULL,
                trade_in_type TEXT NOT NULL,
                trade_in_serial_number TEXT,
                trade_in_nameplate_path TEXT,
                trade_in_product_image_path TEXT,
                invoice_path TEXT,
                FOREIGN KEY (submission_id) REFERENCES submissions (id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_submission(
    *,
    submitted_at: str,
    language: str,
    dealer: Dict[str, Any],
    products: List[Dict[str, Any]],
) -> int:
    """
    Insert a submission and its products.

    Each product dict must contain:
      - product_index
      - sold_model
      - new_serial_number
      - trade_in_type
      - trade_in_serial_number (optional)
      - trade_in_nameplate_path (optional)
      - trade_in_product_image_path (optional)
      - invoice_path (optional)
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO submissions (
                submitted_at,
                language,
                dealer_no,
                company_name,
                postal_location,
                email
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                submitted_at,
                language,
                dealer.get("dealerNo", ""),
                dealer.get("companyName", ""),
                dealer.get("postalLocation", ""),
                dealer.get("email", ""),
            ),
        )
        submission_id = cursor.lastrowid

        for p in products:
            cursor.execute(
                """
                INSERT INTO products (
                    submission_id,
                    product_index,
                    sold_model,
                    new_serial_number,
                    trade_in_type,
                    trade_in_serial_number,
                    trade_in_nameplate_path,
                    trade_in_product_image_path,
                    invoice_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    p["product_index"],
                    p["sold_model"],
                    p["new_serial_number"],
                    p["trade_in_type"],
                    p.get("trade_in_serial_number"),
                    p.get("trade_in_nameplate_path"),
                    p.get("trade_in_product_image_path"),
                    p.get("invoice_path"),
                ),
            )

        conn.commit()
        return int(submission_id)
    finally:
        conn.close()


def fetch_submissions(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Return submissions with their products."""
    conn = get_connection()
    try:
        submissions_rows = conn.execute(
            """
            SELECT *
            FROM submissions
            ORDER BY datetime(submitted_at) DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

        submissions: List[Dict[str, Any]] = []
        for row in submissions_rows:
            sub_id = row["id"]
            products_rows = conn.execute(
                """
                SELECT *
                FROM products
                WHERE submission_id = ?
                ORDER BY product_index ASC, id ASC
                """,
                (sub_id,),
            ).fetchall()

            submissions.append(
                {
                    "id": sub_id,
                    "submitted_at": row["submitted_at"],
                    "language": row["language"],
                    "dealer": {
                        "dealerNo": row["dealer_no"],
                        "companyName": row["company_name"],
                        "postalLocation": row["postal_location"],
                        "email": row["email"],
                    },
                    "products": [
                        {
                            "id": pr["id"],
                            "productIndex": pr["product_index"],
                            "soldModel": pr["sold_model"],
                            "newSerialNumber": pr["new_serial_number"],
                            "tradeInType": pr["trade_in_type"],
                            "tradeInSerialNumber": pr["trade_in_serial_number"],
                            "tradeInNameplatePath": pr["trade_in_nameplate_path"],
                            "tradeInProductImagePath": pr[
                                "trade_in_product_image_path"
                            ],
                            "invoicePath": pr["invoice_path"],
                        }
                        for pr in products_rows
                    ],
                }
            )

        return submissions
    finally:
        conn.close()


