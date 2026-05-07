#!/usr/bin/env bash
set -euo pipefail

IMPORT_DIR="${1:-/private/tmp/apx-mongo-import}"
DATABASE_NAME="${MONGODB_NAME:-energy_aware_ai}"

if [[ -z "${MONGODB_URI:-}" ]]; then
  echo "Set MONGODB_URI before running this import."
  exit 1
fi

import_collection() {
  local collection="$1"
  local upsert_fields="$2"
  local file_path="${IMPORT_DIR}/${collection}.json"

  if [[ ! -f "$file_path" ]]; then
    echo "Missing import file: $file_path"
    exit 1
  fi

  mongoimport \
    --uri "$MONGODB_URI" \
    --db "$DATABASE_NAME" \
    --collection "$collection" \
    --file "$file_path" \
    --jsonArray \
    --mode upsert \
    --upsertFields "$upsert_fields"
}

import_collection "users" "email"
import_collection "experiments" "createdAt,username,mode,modelProfile,workload"
import_collection "simulator_reports" "createdAt,username,title"
import_collection "assistant_chats" "createdAt,username,question"
import_collection "backend_events" "createdAt,eventType,username,email"

echo "MongoDB import completed."
