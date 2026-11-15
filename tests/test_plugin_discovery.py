import sys
sys.path.insert(0, 'src/prostrucvanta')
from app.plugin import PLUGIN

def test_plugin_contract():
    assert PLUGIN.id == 'prostrucvanta'
    assert PLUGIN.path == '/prostrucvanta'
    assert PLUGIN.name == 'ProStrucVanta'
    assert callable(PLUGIN.app_factory)
    print('plugin discovery OK')

if __name__ == '__main__':
    test_plugin_contract()
