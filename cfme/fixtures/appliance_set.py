import pytest
from utils.appliance import provision_appliance_set


@pytest.yield_fixture(scope='function')
def appliance_set(cfme_data):
    appliance_set_data = cfme_data['appliance_provisioning']['appliance_set']
    appliance_set = provision_appliance_set(appliance_set_data, 'rh_updates')

    yield appliance_set

    # Unregister and destroy all
    for appliance in appliance_set.all_appliances:
        with appliance.ssh_client() as ssh:
            ssh.run_command('subscription-manager remove --all')
            ssh.run_command('subscription-manager unregister')
        appliance.destroy()
