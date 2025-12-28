#!/usr/bin/env python3
"""Initialize the database schema."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.database import Database


async def main():
    print("Initializing ClaraVector database...")
    db = Database()
    await db.init()
    print(f"Database created at: {db.db_path}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
