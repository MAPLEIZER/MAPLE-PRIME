from pathlib import Path

import yaml

path = Path(__file__).parents[1] / "sources" / "source-manifest.yaml"
data = yaml.safe_load(path.read_text())
assert data["schema_version"] == 1
for key, source in data["sources"].items():
    for required in ("authority", "category", "type", "url", "parser", "trust"):
        assert source.get(required), f"{key}: missing {required}"
print(f"validated {len(data['sources'])} source definitions")
