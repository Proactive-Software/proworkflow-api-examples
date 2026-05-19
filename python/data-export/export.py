#!/usr/bin/env python3
"""
ProWorkflow API v4 — Full Data Exporter

Downloads all data from the API using fields=all on list endpoints,
fetches single-item detail for core resources, downloads all settings,
and retrieves unique nested data. Avoids duplicate data by only using
root endpoints for resources that also appear under parent routes.

Usage:
    python export.py --base-url https://api.proworkflow.com/api/v4 --api-key YOUR-API-KEY
    python export.py --base-url https://api.proworkflow.com/api/v4 --token YOUR-JWT-TOKEN
    python export.py --config config.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PAGE_SIZE = 30000  # max practical page size (API hard-limit is 30,000)
RATE_LIMIT_PAUSE = 0.07  # seconds between requests (~14 req/s, well under 500/30s)
REQUEST_TIMEOUT = 120  # seconds


# ---------------------------------------------------------------------------
# Endpoint definitions
# ---------------------------------------------------------------------------

# Root list endpoints — these cover all records for each resource type.
# Nested endpoints like /companies/{id}/invoices return subsets of /invoices,
# so we skip them to avoid duplicate data.
ROOT_LIST_ENDPOINTS = [
    # --- Core resources ---
    {
        "path": "/companies",
        "filename": "companies",
        "params": {"fields": "all"},
    },
    {
        "path": "/contacts",
        "filename": "contacts",
        "params": {"fields": "all"},
    },
    {
        "path": "/projects",
        "filename": "projects",
        "params": {"fields": "all,bookmarks", "status": "all"},
    },
    {
        "path": "/invoices",
        "filename": "invoices",
        "params": {"fields": "all", "status": "all"},
    },
    {
        "path": "/quotes",
        "filename": "quotes",
        "params": {"fields": "all", "status": "all"},
    },
    {
        "path": "/messages",
        "filename": "messages",
        "params": {"fields": "all"},
    },
    {
        "path": "/time",
        "filename": "time",
        "params": {
            "fields": "id,contactid,contactname,itemid,projectid,companyid,startdate,starttime,endtime,timespent,notes,billable,accountedfor,itemcollectionid,lastmodifiedutc",
            "trackedfrom": "2000-01-01",  # override default of -6d to get ALL time
            "trackedto": "+0d",
        },
    },
    {
        "path": "/timeallocations",
        "filename": "timeallocations",
        "params": {"fields": "all", "projectstatus": "all"},
    },
    {
        "path": "/files",
        "filename": "files",
        "params": {"fields": "all"},
    },
    {
        "path": "/files/folders",
        "filename": "file_folders",
        "params": {"fields": "all"},
    },

    # --- Sub-resources at root level (avoid nested duplicates) ---
    {
        "path": "/projects/items",
        "filename": "projectitems",
        "params": {"fields": "all", "status": "all"},
    },
    {
        "path": "/projectphases",
        "filename": "projectphases",
        "params": {"fields": "all"},
    },
    {
        "path": "/projectnotes",
        "filename": "projectnotes",
        "params": {"fields": "all"},
    },
    {
        "path": "/invoices/items",
        "filename": "invoiceitems",
        "params": {"fields": "all"},
    },
    {
        "path": "/invoicephases",
        "filename": "invoicephases",
        "params": {"fields": "all"},
    },
    {
        "path": "/quotes/items",
        "filename": "quoteitems",
        "params": {"fields": "all"},
    },
    {
        "path": "/quotephases",
        "filename": "quotephases",
        "params": {"fields": "all"},
    },
    {
        "path": "/templateitems",
        "filename": "templateitems",
        "params": {"fields": "all"},
    },
    {
        "path": "/templatephases",
        "filename": "templatephases",
        "params": {"fields": "all"},
    },
]

# Simple GET endpoints — no pagination, no fields
SIMPLE_ENDPOINTS = [
    # {"path": "/me", "filename": "me"},
]

# Settings endpoints — configuration data, no pagination
SETTINGS_ENDPOINTS = [
    {"path": "/settings/account", "filename": "settings_account"},
    {"path": "/settings/account/license", "filename": "settings_account_license"},
    {"path": "/settings/account/looknfeel", "filename": "settings_account_looknfeel"},
    {"path": "/settings/account/plan", "filename": "settings_account_plan"},
    {"path": "/settings/contacts/divisions", "filename": "settings_contacts_divisions"},
    {"path": "/settings/contacts/groups", "filename": "settings_contacts_groups"},
    {"path": "/settings/contacts/permissions", "filename": "settings_contacts_permissions"},
    {"path": "/settings/contacts/roles", "filename": "settings_contacts_roles"},
    {"path": "/settings/contacts/tags", "filename": "settings_contacts_tags"},
    {"path": "/settings/contacts/teams", "filename": "settings_contacts_teams"},
    {"path": "/settings/invoices/autonumbering", "filename": "settings_invoices_autonumbering"},
    {"path": "/settings/invoices/templates", "filename": "settings_invoices_templates"},
    {"path": "/settings/items/categories", "filename": "settings_items_categories"},
    {"path": "/settings/items/tags", "filename": "settings_items_tags"},
    {"path": "/settings/product/fixedprice", "filename": "settings_product_fixedprice"},
    {"path": "/settings/product/goodservice", "filename": "settings_product_goodservice"},
    {"path": "/settings/product/hourlyservice", "filename": "settings_product_hourlyservice"},
    {"path": "/settings/projects", "filename": "settings_projects"},
    {"path": "/settings/projects/autonumbering", "filename": "settings_projects_autonumbering"},
    {"path": "/settings/projects/categories", "filename": "settings_projects_categories"},
    {"path": "/settings/projects/customfields", "filename": "settings_projects_customfields"},
    {"path": "/settings/projects/tags", "filename": "settings_projects_tags"},
    {"path": "/settings/projects/templates", "filename": "settings_projects_templates"},
    {"path": "/settings/quotes", "filename": "settings_quotes"},
    {"path": "/settings/quotes/autonumbering", "filename": "settings_quotes_autonumbering"},
    {"path": "/settings/quotes/templates", "filename": "settings_quotes_templates"},
    {"path": "/settings/servicerates", "filename": "settings_servicerates"},
    {"path": "/settings/staffrates", "filename": "settings_staffrates"},
    {"path": "/settings/webhooks", "filename": "settings_webhooks"},
    {"path": "/settings/webhooks/requests", "filename": "settings_webhooks_requests"},
    {"path": "/settings/workstages", "filename": "settings_workstages"},
    # {"path": "/settings/workstages/invoice", "filename": "settings_workstages_invoice"},
    # {"path": "/settings/workstages/item", "filename": "settings_workstages_item"},
    # {"path": "/settings/workstages/project", "filename": "settings_workstages_project"},
    # {"path": "/settings/workstages/quote", "filename": "settings_workstages_quote"},
]


# Unique nested endpoints — data only available under a parent resource.
# These are NOT duplicates of any root endpoint.
NESTED_UNIQUE_ENDPOINTS = [
    # Contact-scoped unique data
    # {"parent_list": "contacts", "path": "/contacts/{id}/permissions", "dir": "contacts_permissions"},
    # Company-scoped unique data
    # {"parent_list": "companies", "path": "/companies/{id}/summary", "dir": "companies_summary"},

    # Project-scoped unique data
    # {"parent_list": "projects", "path": "/projects/{id}/settings", "dir": "projects_settings"},
    # {"parent_list": "projects", "path": "/projects/{id}/workstages", "dir": "projects_workstages"},
]


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str, api_key: str | None = None, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        elif api_key:
            self.session.headers["apikey"] = api_key
        else:
            raise ValueError("Provide either --api-key or --token")
        self.session.headers["Accept"] = "application/json"
        self.request_count = 0
        self.error_count = 0

    def get(self, path: str, params: dict | None = None) -> dict | list | None:
        url = f"{self.base_url}{path}"
        time.sleep(RATE_LIMIT_PAUSE)
        try:
            t0 = time.perf_counter()
            resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            self.request_count += 1
            print(f"    {resp.status_code} {path} [{elapsed_ms:.0f}ms]")
        except requests.RequestException as exc:
            print(f"  ERROR: {exc}")
            self.error_count += 1
            return None

        if resp.status_code == 429:
            retry_after = int(resp.headers.get("X-RateLimit-Reset", 30))
            print(f"  Rate limited — waiting {retry_after}s …")
            time.sleep(retry_after)
            return self.get(path, params)

        if resp.status_code == 404:
            return None

        if resp.status_code >= 400:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
            self.error_count += 1
            return None

        try:
            return resp.json()
        except ValueError:
            print(f"  Invalid JSON from {path}")
            self.error_count += 1
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def save_json(output_dir: Path, filename: str, data: Any):
    path = output_dir / f"{filename}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def extract_data(response: dict | list | None) -> list:
    """Pull the 'data' array out of a standard API response."""
    if response is None:
        return []
    if isinstance(response, list):
        return response
    data = response.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def extract_ids(data: list, id_field: str = "id") -> list[int]:
    """Get IDs from a list of records."""
    ids = []
    for item in data:
        if isinstance(item, dict):
            val = item.get(id_field)
            if val is not None:
                try:
                    ids.append(int(val))
                except (ValueError, TypeError):
                    pass
    return sorted(set(ids))


def load_ids_from_file(output_dir: Path, filename: str, id_field: str = "id") -> list[int]:
    """Load IDs from a previously-saved JSON file."""
    path = output_dir / f"{filename}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = extract_data(data) if isinstance(data, dict) else data
    return extract_ids(records, id_field)


# ---------------------------------------------------------------------------
# Download phases
# ---------------------------------------------------------------------------

def download_paginated(client: APIClient, endpoint: dict, output_dir: Path):
    """Download a paginated list endpoint, collecting all pages into one file."""
    path = endpoint["path"]
    filename = endpoint["filename"]
    base_params = dict(endpoint.get("params", {}))

    print(f"\n  {path}")

    # First request — get page 1
    params = {**base_params, "pagenumber": 1, "pagesize": PAGE_SIZE}
    resp = client.get(path, params)
    if resp is None:
        print(f"    FAILED")
        save_json(output_dir, filename, {"status": "error", "data": []})
        return

    all_data = extract_data(resp)
    page = 1
    print(f"    page {page}  ({len(all_data)} records)")

    # If we got a full page, there are likely more rows
    while len(extract_data(resp)) == PAGE_SIZE:
        page += 1
        params = {**base_params, "pagenumber": page, "pagesize": PAGE_SIZE}
        resp = client.get(path, params)
        if resp is None:
            break
        page_data = extract_data(resp)
        if not page_data:
            break
        all_data.extend(page_data)
        print(f"    page {page}  ({len(all_data)} records)")

    save_json(output_dir, filename, all_data)
    print(f"    -> saved {len(all_data)} records to {filename}.json")


def download_simple(client: APIClient, endpoint: dict, output_dir: Path):
    """Download a non-paginated endpoint."""
    path = endpoint["path"]
    filename = endpoint["filename"]

    print(f"\n  {path}")
    resp = client.get(path, endpoint.get("params"))
    if resp is None:
        print(f"    FAILED")
        save_json(output_dir, filename, {"status": "error"})
        return

    save_json(output_dir, filename, resp)
    print(f"    -> saved to {filename}.json")




def download_nested_unique(client: APIClient, endpoint: dict, output_dir: Path):
    """Download unique nested data for each parent ID."""
    parent_list = endpoint["parent_list"]
    path_tpl = endpoint["path"]
    subdir = endpoint["dir"]
    id_field = endpoint.get("id_field", "id")
    base_params = endpoint.get("params", {})

    ids = load_ids_from_file(output_dir, parent_list, id_field)
    if not ids:
        print(f"\n  {path_tpl} — no IDs found in {parent_list}.json, skipping")
        return

    nested_dir = output_dir / subdir
    nested_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  {path_tpl} — {len(ids)} parents")
    fetched = 0
    for parent_id in ids:
        dest = nested_dir / f"{parent_id}.json"
        if dest.exists():
            fetched += 1
            continue

        path = path_tpl.replace("{id}", str(parent_id))
        params = dict(base_params) if base_params else None
        resp = client.get(path, params)
        if resp is not None:
            save_json(nested_dir, str(parent_id), resp)
            fetched += 1
        if fetched % 50 == 0 and fetched > 0:
            print(f"    {fetched}/{len(ids)} …")

    print(f"    -> saved {fetched}/{len(ids)} records to {subdir}/")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="ProWorkflow API v4 data exporter")
    p.add_argument("--base-url", help="API base URL (e.g. https://api.proworkflow.com/api/v4)")
    p.add_argument("--api-key", help="API key for authentication")
    p.add_argument("--token", help="JWT bearer token for authentication")
    p.add_argument("--config", help="Path to JSON config file with base_url, api_key, and/or token")
    p.add_argument("--output", default="output", help="Output directory (default: output)")
    p.add_argument(
        "--skip-nested",
        action="store_true",
        help="Skip unique nested endpoint downloads",
    )
    p.add_argument(
        "--only",
        help="Comma-separated list of phases to run: lists,simple,settings,nested",
    )
    return p.parse_args()


def main():
    args = parse_args()

    base_url = args.base_url
    api_key = args.api_key
    token = args.token

    # Load config file if provided
    if args.config:
        with open(args.config, "r") as f:
            cfg = json.load(f)
        base_url = base_url or cfg.get("base_url")
        api_key = api_key or cfg.get("api_key")
        token = token or cfg.get("token")

    if not base_url:
        print("Error: --base-url is required (or set base_url in config.json)")
        sys.exit(1)
    if not api_key and not token:
        print("Error: --api-key or --token is required")
        sys.exit(1)

    # Determine which phases to run
    phases = {"lists", "simple", "settings", "nested"}
    if args.only:
        phases = set(args.only.split(","))
    if args.skip_nested:
        phases.discard("nested")

    client = APIClient(base_url, api_key=api_key, token=token)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    start = datetime.now()
    print(f"ProWorkflow API v4 Data Export")
    print(f"Base URL: {base_url}")
    print(f"Output:   {output_dir.resolve()}")
    print(f"Phases:   {', '.join(sorted(phases))}")
    print(f"Started:  {start.isoformat()}")

    # --- Phase 1: Root list endpoints (paginated) ---
    if "lists" in phases:
        print(f"\n{'='*60}")
        print(f"PHASE 1: Root list endpoints")
        print(f"{'='*60}")
        for ep in ROOT_LIST_ENDPOINTS:
            download_paginated(client, ep, output_dir)

    # --- Phase 2: Simple endpoints ---
    if "simple" in phases:
        print(f"\n{'='*60}")
        print(f"PHASE 2: Simple endpoints")
        print(f"{'='*60}")
        for ep in SIMPLE_ENDPOINTS:
            download_simple(client, ep, output_dir)

    # --- Phase 3: Settings endpoints ---
    if "settings" in phases:
        print(f"\n{'='*60}")
        print(f"PHASE 3: Settings endpoints")
        print(f"{'='*60}")
        for ep in SETTINGS_ENDPOINTS:
            download_simple(client, ep, output_dir)

    # --- Phase 4: Unique nested endpoints ---
    if "nested" in phases:
        print(f"\n{'='*60}")
        print(f"PHASE 4: Unique nested endpoints")
        print(f"{'='*60}")
        for ep in NESTED_UNIQUE_ENDPOINTS:
            download_nested_unique(client, ep, output_dir)

    # --- Summary ---
    elapsed = datetime.now() - start
    print(f"\n{'='*60}")
    print(f"EXPORT COMPLETE")
    print(f"{'='*60}")
    print(f"Requests: {client.request_count}")
    print(f"Errors:   {client.error_count}")
    print(f"Elapsed:  {elapsed}")
    print(f"Output:   {output_dir.resolve()}")

    # Save a manifest
    save_json(output_dir, "_manifest", {
        "exported_at": start.isoformat(),
        "base_url": base_url,
        "requests": client.request_count,
        "errors": client.error_count,
        "elapsed_seconds": elapsed.total_seconds(),
        "phases": sorted(phases),
    })


if __name__ == "__main__":
    main()
