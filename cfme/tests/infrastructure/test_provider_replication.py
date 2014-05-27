import cfme.web_ui.flash as flash
from utils import testgen

pytest_generate_tests = testgen.generate(testgen.infra_providers, scope="module")


def test_provision_appliance_set(appliance_set, provider_crud):
    """Tests that a provider added to the host appliance replicates
        to other appliances in the region.
    """
    with appliance_set.primary.browser_session():
        provider_crud.create()
        flash.assert_message_match('Infrastructure Providers "%s" was saved' % provider_crud.name)
    for appl in appliance_set.secondary:
        with appl.browser_session():
            assert provider_crud.exists
