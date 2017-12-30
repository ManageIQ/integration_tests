import pytest

from wrapanapi.containers.volume import Volume as VolumeApi
from cfme.containers.volume import Volume


@pytest.yield_fixture(scope='module')
def has_persistent_volume(provider, appliance):
    """Verifying that some persistent volume exists"""
    name = 'pv-{}'.format(len(provider.mgmt.list_volume()) + 1)
    payload = {
        'metadata': {'name': name},
        'spec': {
            'accessModes': ['ReadWriteOnce'],
            'capacity': {'storage': '1Gi'},
            'nfs': {
                'path': '/tmp',
                'server': '12.34.56.78'
            }
        },
        'persistentVolumeReclaimPolicy': 'Retain'
    }
    volume = VolumeApi.create(provider.mgmt, payload)
    yield Volume(volume.name, provider, appliance)
    volume.delete()
