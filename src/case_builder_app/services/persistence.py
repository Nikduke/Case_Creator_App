from __future__ import annotations

import json
from pathlib import Path

from case_builder_app.models import Project


PROJECT_FILE_SUFFIX = ".casebuilder.json"


class PersistenceService:
    def save_project(self, path: str | Path, project: Project) -> None:
        file_path = Path(path)
        if file_path.suffix.lower() != ".json" and not file_path.name.endswith(PROJECT_FILE_SUFFIX):
            file_path = file_path.with_name(file_path.name + PROJECT_FILE_SUFFIX)
        file_path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")

    def load_project(self, path: str | Path) -> Project:
        file_path = Path(path)
        return Project.from_dict(json.loads(file_path.read_text(encoding="utf-8")))

