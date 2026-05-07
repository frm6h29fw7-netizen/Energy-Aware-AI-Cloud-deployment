from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError as exc:
    raise SystemExit("Install dependencies first: python3 -m pip install -r requirements.txt") from exc

try:
    import certifi
except ImportError:
    certifi = None


ROOT = Path(__file__).resolve().parent.parent
USERS_FILE = ROOT / "user-accounts.json"
HISTORY_FILE = ROOT / "experiment-history.csv"
REPORTS_FILE = ROOT / "simulator-reports.json"
ASSISTANT_HISTORY_FILE = ROOT / "assistant-history.json"
BACKEND_EVENTS_FILE = ROOT / "backend-events.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Move local prototype data into MongoDB Atlas or local MongoDB.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated without writing to MongoDB.")
    parser.add_argument("--export-dir", help="Write MongoDB-ready JSON array files to this directory.")
    args = parser.parse_args()

    documents = {
        "users": load_users(),
        "experiments": load_experiments(),
        "simulator_reports": load_json_records(REPORTS_FILE),
        "assistant_chats": load_json_records(ASSISTANT_HISTORY_FILE),
        "backend_events": load_json_records(BACKEND_EVENTS_FILE),
    }

    if args.dry_run:
        print_summary(documents, "Dry run")
        return

    if args.export_dir:
        export_dir = Path(args.export_dir).expanduser().resolve()
        export_dir.mkdir(parents=True, exist_ok=True)
        for collection, rows in documents.items():
            output_path = export_dir / f"{collection}.json"
            output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print_summary(documents, f"Exported JSON files to {export_dir}")
        return

    uri = os.environ.get("MONGODB_URI")
    db_name = os.environ.get("MONGODB_NAME", "energy_aware_ai")
    allow_invalid_certificates = os.environ.get("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"
    if not uri:
        raise SystemExit("Set MONGODB_URI before running this migration.")

    client_options: dict[str, Any] = {"serverSelectionTimeoutMS": 10000}
    if allow_invalid_certificates:
        client_options["tlsAllowInvalidCertificates"] = True
    elif certifi is not None and uri.startswith("mongodb+srv://"):
        client_options["tlsCAFile"] = certifi.where()

    try:
        client = MongoClient(uri, **client_options)
        client.admin.command("ping")
    except PyMongoError as exc:
        raise SystemExit(f"Could not connect to MongoDB: {exc}") from exc

    db = client[db_name]
    results = {
        "users": upsert_many(db.users, documents["users"], ["email"]),
        "experiments": upsert_many(db.experiments, documents["experiments"], ["createdAt", "username", "mode", "modelProfile", "workload"]),
        "simulator_reports": upsert_many(db.simulator_reports, documents["simulator_reports"], ["createdAt", "username", "title"]),
        "assistant_chats": upsert_many(db.assistant_chats, documents["assistant_chats"], ["createdAt", "username", "question"]),
        "backend_events": upsert_many(db.backend_events, documents["backend_events"], ["createdAt", "eventType", "username", "email"]),
    }

    print_summary(documents, "Migrated")
    for collection, result in results.items():
        print(f"{collection}: inserted/updated {result}")


def load_users() -> list[dict[str, Any]]:
    if not USERS_FILE.exists():
        return []
    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [user for user in data.values() if isinstance(user, dict)]
    return []


def load_experiments() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    with HISTORY_FILE.open(newline="", encoding="utf-8") as handle:
        return [normalise_row(row) for row in csv.DictReader(handle)]


def load_json_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def normalise_row(row: dict[str, str]) -> dict[str, Any]:
    numeric_fields = {
        "requests",
        "modelSize",
        "optimisation",
        "utilisation",
        "carbonIntensity",
        "energyKwh",
        "carbonKg",
        "latencyMs",
        "accuracyPercent",
        "costGbp",
        "cpuPercent",
        "gpuPercent",
        "memoryMb",
        "throughputRps",
        "efficiencyScore",
    }
    output: dict[str, Any] = {}
    for key, value in row.items():
        if key in numeric_fields:
            output[key] = parse_number(value)
        else:
            output[key] = value
    output.setdefault("storageBackend", "Migrated from JSON + CSV fallback")
    return output


def parse_number(value: str) -> float | int | str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


def upsert_many(collection, documents: list[dict[str, Any]], unique_fields: list[str]) -> int:
    changed = 0
    for document in documents:
        if not isinstance(document, dict):
            continue
        filter_doc = {field: document.get(field) for field in unique_fields if document.get(field) not in (None, "")}
        if not filter_doc:
            filter_doc = document
        result = collection.update_one(filter_doc, {"$set": document}, upsert=True)
        if result.upserted_id is not None or result.modified_count:
            changed += 1
    return changed


def print_summary(documents: dict[str, list[dict[str, Any]]], title: str) -> None:
    print(title)
    for collection, rows in documents.items():
        print(f"{collection}: {len(rows)} record(s)")


if __name__ == "__main__":
    main()
