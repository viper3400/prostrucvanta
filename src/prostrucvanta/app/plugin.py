from types import SimpleNamespace
from .main import create_app
from .version import APP_VERSION

PLUGIN = SimpleNamespace(
    id="prostrucvanta",
    name="ProStrucVanta",
    description="Lightweight project and task management",
    version=APP_VERSION,
    path="/prostrucvanta",
    app_factory=lambda: create_app(),
)
