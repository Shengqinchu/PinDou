"""Copy PinDou data from local SQLite into a MySQL database.

Usage:
    python scripts/sqlite_to_mysql.py --sqlite sqlite:///./var/pindou.db --mysql mysql+pymysql://...

The script is intentionally table-order aware so foreign keys can be restored
without disabling constraints. It upserts by primary key, making it safe to
resume after an interrupted migration.
"""

from __future__ import annotations

import argparse
from typing import Iterable

from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.engine import Engine


TABLE_ORDER = [
    "users",
    "artworks",
    "orders",
    "cdks",
    "consent_logs",
    "daily_quotas",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate PinDou SQLite data to MySQL.")
    parser.add_argument("--sqlite", default="sqlite:///./var/pindou.db", help="Source SQLite DATABASE_URL")
    parser.add_argument("--mysql", required=True, help="Destination MySQL DATABASE_URL")
    parser.add_argument("--dry-run", action="store_true", help="Count rows without writing to MySQL")
    args = parser.parse_args()

    source = create_engine(args.sqlite, future=True)
    target = create_engine(args.mysql, future=True, pool_pre_ping=True)
    migrate(source, target, dry_run=args.dry_run)
    return 0


def migrate(source: Engine, target: Engine, *, dry_run: bool = False) -> None:
    source_meta = MetaData()
    source_meta.reflect(bind=source)
    target_meta = MetaData()
    target_meta.reflect(bind=target)

    with source.connect() as source_conn, target.begin() as target_conn:
        for table_name in existing_tables(TABLE_ORDER, source_meta.tables):
            source_table = source_meta.tables[table_name]
            target_table = target_meta.tables[table_name]
            rows = [dict(row._mapping) for row in source_conn.execute(select(source_table))]
            print(f"{table_name}: {len(rows)} rows")
            if dry_run or not rows:
                continue

            primary_keys = [column.name for column in target_table.primary_key.columns]
            stmt = mysql_insert(target_table).values(rows)
            update_columns = {
                column.name: stmt.inserted[column.name]
                for column in target_table.columns
                if column.name not in primary_keys
            }
            if update_columns:
                stmt = stmt.on_duplicate_key_update(**update_columns)
            else:
                stmt = stmt.prefix_with("IGNORE")
            target_conn.execute(stmt)


def existing_tables(table_order: Iterable[str], tables) -> list[str]:
    return [name for name in table_order if name in tables]


if __name__ == "__main__":
    raise SystemExit(main())
