#!/usr/bin/env bash
# Exporte le spec OpenAPI du backend vers docs/reference/openapi.json.
#
# Le spec committé sert de contrat versionné pour les clients externes -
# notamment la génération du client Dart typé du companion mobile :
#   openapi-generator generate -i docs/reference/openapi.json -g dart-dio ...
#
# À relancer après tout changement de routes/schemas backend.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose run --rm --no-deps --entrypoint python backend -c '
import json
from backend.main import app
print(json.dumps(app.openapi(), ensure_ascii=False, indent=1, sort_keys=True))
' 2>/dev/null > docs/reference/openapi.json

python3 -c "import json; d=json.load(open('docs/reference/openapi.json')); print(f\"OK - {len(d['paths'])} routes -> docs/reference/openapi.json\")"
