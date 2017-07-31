import pytest


roles_ui_workload = ['automate', 'reporting', 'scheduler', 'user_interface', 'web_services',
    'websocket']


@pytest.fixture(scope='session')
def set_server_roles_ui_workload_session(appliance):
    appliance.server_roles(','.join(roles_ui_workload))
