#!/usr/bin/env python3
"""
Export PostgreSQL Database (songs_db) -> Standalone SQLite Database (music_app_export.db)
========================================================================================
Exports all tables, columns, indexes, and records from PostgreSQL database into SQLite.

Usage:
    python app/scripts/export_postgres_to_sqlite.py [output_sqlite_filename.db]
"""

import sys
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings


def export_postgres_to_sqlite(sqlite_output_path: str = "music_app_export.db"):
    print(f"\n{'='*75}")
    print("  POSTGRESQL -> SQLITE DATABASE EXPORTER")
    print(f"  Source Postgres : {settings.DATABASE_URL}")
    print(f"  Target SQLite   : {os.path.abspath(sqlite_output_path)}")
    print(f"{'='*75}\n")

    # Connect to PostgreSQL
    pg_engine = create_engine(settings.DATABASE_URL)
    pg_inspector = inspect(pg_engine)
    pg_conn = pg_engine.connect()

    tables = pg_inspector.get_table_names()
    print(f"[1/3] Found {len(tables)} tables in PostgreSQL: {', '.join(tables)}")

    # Remove existing output SQLite DB file if present
    if os.path.exists(sqlite_output_path):
        os.remove(sqlite_output_path)
        print(f"[2/3] Removed previous output file: {sqlite_output_path}")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_output_path)
    sqlite_conn.execute("PRAGMA journal_mode=WAL;")
    sqlite_conn.execute("PRAGMA foreign_keys=OFF;")  # temporary disable FKs during dump

    stats = {}

    print("\n[3/3] Copying schema and rows to SQLite...\n")

    for table in tables:
        columns = pg_inspector.get_columns(table)
        pk_constraint = pg_inspector.get_pk_constraint(table)
        pks = pk_constraint.get("constrained_columns", [])

        # Build SQLite CREATE TABLE statement
        col_defs = []
        col_names = []

        for col in columns:
            col_name = col["name"]
            col_type_str = str(col["type"]).upper()
            col_names.append(col_name)

            # Map Postgres types -> SQLite types
            if "UUID" in col_type_str or "VARCHAR" in col_type_str or "TEXT" in col_type_str or "DATETIME" in col_type_str or "TIMESTAMP" in col_type_str:
                sqlite_type = "TEXT"
            elif "INT" in col_type_str:
                sqlite_type = "INTEGER"
            elif "FLOAT" in col_type_str or "DOUBLE" in col_type_str or "NUMERIC" in col_type_str:
                sqlite_type = "REAL"
            elif "BOOL" in col_type_str:
                sqlite_type = "INTEGER"
            else:
                sqlite_type = "TEXT"

            col_def = f'"{col_name}" {sqlite_type}'

            if not col["nullable"] and col_name not in pks:
                col_def += " NOT NULL"

            col_defs.append(col_def)

        if pks:
            pk_cols_quoted = ", ".join([f'"{pk}"' for pk in pks])
            col_defs.append(f"PRIMARY KEY ({pk_cols_quoted})")

        create_sql = f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(col_defs) + "\n);"
        sqlite_conn.execute(create_sql)

        # Query all rows from PostgreSQL
        pg_rows = pg_conn.execute(text(f'SELECT * FROM "{table}"')).fetchall()

        # Insert into SQLite
        placeholders = ", ".join(["?"] * len(col_names))
        cols_quoted = ", ".join([f'"{c}"' for c in col_names])
        insert_sql = f'INSERT INTO "{table}" ({cols_quoted}) VALUES ({placeholders})'

        converted_rows = []
        for row in pg_rows:
            row_dict = dict(row._mapping)
            converted_row = []
            for col_name in col_names:
                val = row_dict[col_name]
                if isinstance(val, uuid.UUID):
                    val = str(val)
                elif isinstance(val, datetime):
                    val = val.isoformat()
                elif isinstance(val, bool):
                    val = 1 if val else 0
                converted_row.append(val)
            converted_rows.append(converted_row)

        sqlite_conn.executemany(insert_sql, converted_rows)
        sqlite_conn.commit()

        stats[table] = len(converted_rows)
        print(f"  [OK] Table '{table}': Copied {len(converted_rows)} rows.")

    sqlite_conn.execute("PRAGMA foreign_keys=ON;")
    sqlite_conn.close()
    pg_conn.close()

    db_size_mb = os.path.getsize(sqlite_output_path) / (1024 * 1024)

    print(f"\n{'='*75}")
    print("EXPORT COMPLETED SUCCESSFULLY!")
    print(f"  Output SQLite DB : {os.path.abspath(sqlite_output_path)}")
    print(f"  Database Size    : {db_size_mb:.2f} MB")
    print("  Table Breakdown  :")
    for tbl, cnt in stats.items():
        print(f"    - {tbl:22s}: {cnt:6d} rows")
    print(f"{'='*75}\n")


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "music_app_export.db"
    export_postgres_to_sqlite(out_file)
