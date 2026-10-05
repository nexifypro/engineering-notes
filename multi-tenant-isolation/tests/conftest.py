import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADMIN_URL = os.environ.get("TENANTS_ADMIN_URL", "postgresql://postgres@localhost:5499/tenants")


def psql_value(command: str) -> str:
    """One scalar from the admin connection, no headers or footers."""
    return subprocess.run(["psql", ADMIN_URL, "-tAc", command], check=True, capture_output=True, text=True).stdout.strip()


def psql(sql_file: Path | None = None, command: str | None = None) -> str:
    args = ["psql", ADMIN_URL, "-v", "ON_ERROR_STOP=1", "-q"]
    args += ["-f", str(sql_file)] if sql_file else ["-c", command]
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


@pytest.fixture(scope="session", autouse=True)
def database():
    psql(command="DROP SCHEMA public CASCADE; CREATE SCHEMA public; DROP VIEW IF EXISTS revenue_by_month;")
    psql(ROOT / "sql" / "001_schema.sql")
    psql(ROOT / "sql" / "002_seed.sql")
    yield
