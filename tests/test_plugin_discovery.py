import sys
sys.path.insert(0, 'src/pyprojects')
from app.plugin import PLUGIN

def test_plugin_contract():
    assert PLUGIN.id == 'pyprojects'
    assert PLUGIN.path == '/pyprojects'
    assert PLUGIN.name == 'PyProjects'
    assert callable(PLUGIN.app_factory)
    print('plugin discovery OK')

if __name__ == '__main__':
    test_plugin_contract()
