import pytest

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
    assert provider.mgmt.api.post('persistentvolume', payload)[0] in [200, 201]
    # TODO: switch to below once wrapanapi version > 2.4.4:
    #     from wrapanapi.containers.volume import Volume as VolumeApi
    #     volume = VolumeApi.create(provider, payload)
    yield Volume(name, provider, appliance)
    provider.mgmt.api.delete('persistentvolume', name)
