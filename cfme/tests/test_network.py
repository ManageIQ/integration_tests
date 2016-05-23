import pytest
from utils.log import logger


@pytest.mark.parametrize("run_number", range(10))
def test_network_stability(run_number):
    ssh_client = pytest.store.current_appliance.ssh_client
    try:
        with ssh_client as ssh:
            for i in range(0, 8):
                logger.info('Attempt {}'.format(i))
                ssh.run_command('ls ~')
                ssh.run_command('pwd')
                ssh.run_command('systemctl status evmserverd')
                ssh.run_command('systemctl status rh-postgresql94-postgresql')
                ssh.run_command('sleep 15')
    except Exception as ex:
        pytest.fail(str(ex))
