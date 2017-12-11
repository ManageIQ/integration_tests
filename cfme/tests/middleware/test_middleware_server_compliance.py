import fauxfactory
import pytest
from cfme.control.explorer.policies import MiddlewareServerCompliancePolicy
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.utils.version import current_version
from server_methods import (
    get_eap_server,
    get_hawkular_server,
    get_domain_server,
    verify_server_compliant
)


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.9'),
    pytest.mark.provider([HawkularProvider], scope="function"),
]


@pytest.yield_fixture(scope="function")
def server(provider):
    server = get_eap_server(provider)
    yield server


@pytest.yield_fixture(scope="function")
def domain_server(provider):
    server = get_domain_server(provider)
    yield server


@pytest.yield_fixture(scope="function")
def hawkular_server(provider):
    server = get_hawkular_server(provider)
    yield server


@pytest.yield_fixture(scope="function")
def policy_for_testing_eap(appliance, server):
    policy_profile = _create_policy_profile(appliance, 'EAP')
    server.assign_policy_profiles(policy_profile.description)
    yield
    server.unassign_policy_profiles(policy_profile.description)
    _delete_policy_profile(appliance, policy_profile)


@pytest.yield_fixture(scope="function")
def policy_for_testing_eap_domain(appliance, domain_server):
    policy_profile = _create_policy_profile(appliance, 'EAP')
    domain_server.assign_policy_profiles(policy_profile.description)
    yield
    domain_server.unassign_policy_profiles(policy_profile.description)
    _delete_policy_profile(appliance, policy_profile)


@pytest.yield_fixture(scope="function")
def policy_for_testing_hawkular(appliance, hawkular_server):
    policy_profile = _create_policy_profile(appliance, 'Hawkular')
    hawkular_server.assign_policy_profiles(policy_profile.description)
    yield
    hawkular_server.unassign_policy_profiles(policy_profile.description)
    _delete_policy_profile(appliance, policy_profile)


def _create_policy_profile(appliance, server_name):
    policy = appliance.collections.policies.create(
        MiddlewareServerCompliancePolicy,
        fauxfactory.gen_alpha(),
        scope="fill_field(Middleware Server : Product, INCLUDES, {})".format(server_name)
    )
    policy_profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alpha(), policies=[policy])
    return policy_profile


def _delete_policy_profile(appliance, policy_profile):
        policy = policy_profile.policies[0]
        policy_profile.delete()
        policy.delete()


def test_server_compliance(provider, server, policy_for_testing_eap):
    """Tests executing "Check Compliance of last known configuration menu item for EAP7 Server.
    Verifies that success message is shown.
    Verifies that server is Compliant
    """
    server.check_compliance()
    verify_server_compliant(provider, server)


def test_domain_server_compliance(provider, domain_server, policy_for_testing_eap_domain):
    """Tests executing "Check Compliance of last known configuration menu item for Domain Server.
    Verifies that success message is shown.
    Verifies that server is Compliant
    """
    domain_server.check_compliance()
    verify_server_compliant(provider, domain_server)


def test_hawkular_compliance(provider, hawkular_server, policy_for_testing_hawkular):
    """Tests executing "Check Compliance of last known configuration menu item for Hawkular Server.
    Verifies that success message is shown.
    Verifies that server is Compliant
    """
    hawkular_server.check_compliance()
    verify_server_compliant(provider, hawkular_server)
