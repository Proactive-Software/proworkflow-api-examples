#!/usr/bin/env python3
"""
ProWorkflow API v4 — Contacts CSV Importer

Reads contacts from a CSV file and creates them via the API.
Supports dry-run mode to preview what would be created without making any changes.

Usage:
    python import_contacts.py --base-url https://api.proworkflow.com/api/v4 --api-key YOUR-API-KEY --file contacts.csv
    python import_contacts.py --config config.json --file contacts.csv --dry-run
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import urllib3
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RATE_LIMIT_PAUSE = 0.07  # seconds between requests (~14 req/s, well under 500/30s)
REQUEST_TIMEOUT = 30

# CSV columns that map directly to API fields (string values)
STRING_FIELDS = [
    "firstname", "lastname", "type", "email", "workphone", "mobilephone",
    "title", "address1", "address2", "address3", "city", "state",
    "zipcode", "country", "emailsignature",
]

# CSV columns that are integers (empty = omit)
INT_FIELDS = ["companyid", "divisionid"]

# Valid contact types
VALID_TYPES = {"client", "contractor", "staff", "other", "supplier"}


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str, api_key: str | None = None, token: str | None = None, insecure: bool = False):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.verify = not insecure
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        elif api_key:
            self.session.headers["apikey"] = api_key
        else:
            raise ValueError("Provide either --api-key or --token")
        self.session.headers["Content-Type"] = "application/json"
        self.session.headers["Accept"] = "application/json"

    def post(self, path: str, body: dict) -> tuple[int, dict | None]:
        url = f"{self.base_url}{path}"
        time.sleep(RATE_LIMIT_PAUSE)
        try:
            resp = self.session.post(url, json=body, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            return 0, {"error": str(exc)}

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("X-RateLimit-Reset", 30))
            print(f"  Rate limited — waiting {retry_after}s …")
            time.sleep(retry_after)
            return self.post(path, body)

        try:
            return resp.status_code, resp.json()
        except ValueError:
            return resp.status_code, None


# ---------------------------------------------------------------------------
# CSV parsing
# ---------------------------------------------------------------------------

def parse_row(row: dict, row_num: int) -> tuple[dict | None, list[str]]:
    """Convert a CSV row to an API payload. Returns (payload, errors)."""
    errors = []
    payload = {}

    for field in STRING_FIELDS:
        val = row.get(field, "").strip()
        if val:
            payload[field] = val

    for field in INT_FIELDS:
        val = row.get(field, "").strip()
        if val:
            try:
                payload[field] = int(val)
            except ValueError:
                errors.append(f"  row {row_num}: '{field}' must be a number, got '{val}'")

    # allowlogin defaults to false if not provided
    allow_login_val = row.get("allowlogin", "").strip().lower()
    if allow_login_val in ("true", "1", "yes"):
        payload["allowlogin"] = True
    else:
        payload["allowlogin"] = False

    # Required: at least one of firstname or lastname
    if not payload.get("firstname") and not payload.get("lastname"):
        errors.append(f"  row {row_num}: 'firstname' or 'lastname' is required")

    # Validate type if provided
    contact_type = payload.get("type", "")
    if contact_type and contact_type not in VALID_TYPES:
        errors.append(f"  row {row_num}: 'type' must be one of {', '.join(sorted(VALID_TYPES))}, got '{contact_type}'")

    return (payload if not errors else None), errors


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    """Load and validate all rows from CSV. Returns (rows, all_errors)."""
    all_payloads = []
    all_errors = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # row 1 = header
            payload, errors = parse_row(row, i)
            if errors:
                all_errors.extend(errors)
            else:
                all_payloads.append(payload)

    return all_payloads, all_errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="ProWorkflow contacts CSV importer")
    p.add_argument("--base-url", help="API base URL (e.g. https://api.proworkflow.com/api/v4)")
    p.add_argument("--api-key", help="API key for authentication")
    p.add_argument("--token", help="JWT bearer token for authentication")
    p.add_argument("--config", help="Path to JSON config file with base_url, api_key, and/or token")
    p.add_argument("--file", required=True, help="Path to CSV file")
    p.add_argument("--dry-run", action="store_true", help="Preview rows without creating contacts")
    p.add_argument("--insecure", action="store_true", help="Skip SSL certificate verification (local dev only)")
    return p.parse_args()


def main():
    args = parse_args()

    base_url = args.base_url
    api_key = args.api_key
    token = args.token

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        base_url = base_url or cfg.get("base_url")
        api_key = api_key or cfg.get("api_key")
        token = token or cfg.get("token")

    if not args.dry_run:
        if not base_url:
            print("Error: --base-url is required (or set base_url in config.json)")
            sys.exit(1)
        if not api_key and not token:
            print("Error: --api-key or --token is required")
            sys.exit(1)

    csv_path = Path(args.file)
    if not csv_path.exists():
        print(f"Error: file not found: {csv_path}")
        sys.exit(1)

    print(f"Loading {csv_path} …")
    payloads, errors = load_csv(csv_path)

    if errors:
        print(f"\n{len(errors)} validation error(s):")
        for e in errors:
            print(e)
        sys.exit(1)

    print(f"  {len(payloads)} contact(s) ready to import")

    if args.dry_run:
        print("\n--- DRY RUN (no contacts created) ---")
        for i, p in enumerate(payloads, start=1):
            name = " ".join(filter(None, [p.get("firstname"), p.get("lastname")]))
            print(f"  [{i}] {name} ({p.get('type', 'no type')}) — {p.get('email', 'no email')}")
        return

    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    client = APIClient(base_url, api_key=api_key, token=token, insecure=args.insecure)

    created = 0
    failed = 0

    print("\nImporting …")
    for i, payload in enumerate(payloads, start=1):
        name = " ".join(filter(None, [payload.get("firstname"), payload.get("lastname")]))
        status_code, resp = client.post("/contacts", payload)

        if status_code in (200, 201):
            created += 1
            contact_id = "?"
            if isinstance(resp, dict):
                data = resp.get("data")
                if isinstance(data, dict):
                    contact_id = data.get("id", "?")
                elif isinstance(data, list) and data and isinstance(data[0], dict):
                    contact_id = data[0].get("id", "?")
            print(f"  [{i}/{len(payloads)}] created  id={contact_id}  {name}")
        else:
            failed += 1
            detail = ""
            if isinstance(resp, dict):
                data = resp.get("data", resp.get("error", ""))
                detail = str(data)[:120]
            print(f"  [{i}/{len(payloads)}] FAILED   {name}  HTTP {status_code}  {detail}")

    print(f"\nDone — {created} created, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
