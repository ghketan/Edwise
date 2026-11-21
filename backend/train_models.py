import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.database import SessionLocal
from backend.app.ml_engine.trainer import train_and_save_artifacts
from backend.app.models.ml import ModelRegistry


def main():
    print("Executing offline model training protocol (D-007, D-015)...")
    meta = train_and_save_artifacts()
    db = SessionLocal()
    try:
        has_active_reg = (
            db.query(ModelRegistry)
            .filter(ModelRegistry.task == "regression", ModelRegistry.is_active.is_(True))
            .first()
            is not None
        )
        for task_name, task_data in meta.items():
            existing = db.query(ModelRegistry).filter(ModelRegistry.version == task_data["version"]).first()
            if not existing:
                reg = ModelRegistry(
                    model_name=task_data["model_name"],
                    version=task_data["version"],
                    task=task_data["task"],
                    data_source=task_data["data_source"],
                    is_synthetic=task_data["is_synthetic"],
                    feature_list=task_data["features"],
                    split_method=task_data["split_method"],
                    metrics=task_data["metrics"],
                    artifact_path=task_data["artifact_path"],
                    is_active=(task_data["task"] != "regression" or (not has_active_reg and task_name == "regression")),
                    trained_by="train_script"
                )
                db.add(reg)
                if reg.task == "regression" and reg.is_active:
                    has_active_reg = True
            else:
                existing.metrics = task_data["metrics"]
                existing.artifact_path = task_data["artifact_path"]
        db.commit()
        print("Model training protocol finished and registry updated.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

