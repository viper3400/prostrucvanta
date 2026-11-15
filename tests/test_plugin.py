import sys
sys.path.insert(0, 'src/pyprojects')
from app.plugin import PLUGIN

def test_plugin_contract():
    assert PLUGIN.id == 'pyprojects'
    assert PLUGIN.path == '/pyprojects'
    assert callable(PLUGIN.app_factory)
