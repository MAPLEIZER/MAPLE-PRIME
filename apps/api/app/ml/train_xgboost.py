from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import MobileTelemetryEventRecord
from app.ml.dataset import FEATURE_NAMES, build_training_rows

MIN_TRAINING_ROWS = 50


def train(output_dir: Path, *, database_url: str | None = None) -> tuple[Path, Path]:
    try:
        import xgboost as xgb
    except ImportError as exc:
        raise RuntimeError("Install the optional ML dependencies with: pip install -e '.[ml]'") from exc

    engine = create_engine(database_url or get_settings().database_url)
    with Session(engine) as session:
        records = list(
            session.scalars(
                select(MobileTelemetryEventRecord).where(MobileTelemetryEventRecord.user_label.is_not(None))
            )
        )
    rows = build_training_rows(records)
    labels = sorted({row.label for row in rows})
    if len(rows) < MIN_TRAINING_ROWS:
        raise RuntimeError(f"Need at least {MIN_TRAINING_ROWS} explicitly labeled rows; found {len(rows)}")
    if len(labels) < 2:
        raise RuntimeError("Need at least two user-labeled classes before training")

    label_to_id = {label: index for index, label in enumerate(labels)}
    x_values = [list(row.features) for row in rows]
    y_values = [label_to_id[row.label] for row in rows]

    model = xgb.XGBClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=2,
        reg_lambda=1.0,
        objective="multi:softprob",
        eval_metric="mlogloss",
        tree_method="hist",
        n_jobs=2,
        random_state=42,
    )
    model.fit(x_values, y_values)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "loan-message-xgboost.json"
    manifest_path = output_dir / "loan-message-xgboost.manifest.json"
    model.save_model(model_path)
    manifest_path.write_text(
        json.dumps(
            {
                "model_type": "xgboost",
                "feature_schema": "kdr-msg-v1",
                "feature_names": list(FEATURE_NAMES),
                "labels": labels,
                "training_rows": len(rows),
                "trained_at": datetime.now(UTC).isoformat(),
                "privacy": "trained from explicitly user-labeled derived features; no raw SMS bodies",
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    return model_path, manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the optional KDR loan-message XGBoost model")
    parser.add_argument("--output", type=Path, default=Path("local-data/models"))
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    model_path, manifest_path = train(args.output, database_url=args.database_url)
    print(model_path)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
