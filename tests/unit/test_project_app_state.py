from core.composition import Composition
from core.project_manager import ProjectManager


def test_project_persists_effect_and_automation_settings(tmp_path) -> None:
    manager = ProjectManager()
    path = tmp_path / "look-and-automation.eliav"
    app_state = {
        "effects": {"preset_name": "VHS / Tape", "grain": 0.34},
        "automation_settings": {"loop_probability": 0.75},
    }

    manager.save(path, Composition(), [], app_state=app_state)
    manager.load(path)

    assert manager.last_app_state == app_state
