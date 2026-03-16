"""
Run once to create Delta tables in Databricks.
Reads DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_WAREHOUSE_ID from .env or environment.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from backend import databricks_client as db


async def main() -> None:
    if not db.is_configured():
        print("ERROR: DATABRICKS_HOST, DATABRICKS_TOKEN or DATABRICKS_WAREHOUSE_ID not set.")
        print("Add them to your .env file and try again.")
        sys.exit(1)

    print(f"Host:       {db._host()}")
    print(f"Warehouse:  {db._warehouse_id()}")
    print("Creating tables...")
    await db.ensure_tables()
    print("Done.")


asyncio.run(main())
