# -*- coding: utf-8 -*-
import pytest
from widgetastic.exceptions import MoveTargetOutOfBoundsException

from cfme.utils import error
from cfme.utils.blockers import BZ
from cfme.common.provider_views import NetworkProvidersView
from cfme import test_requirements
from cfme.networks.provider.nuage import NuageProvider, NetworkProvider

pytestmark = [
    pytest.mark.provider([NetworkProvider], scope="module"),
    test_requirements.discovery,
    pytest.mark.ignore_stream('5.8'),
    pytest.mark.meta(blockers=[BZ(1518301, forced_streams=['5.9'])])
]


def test_add_cancelled_validation(request):
    """Tests that the flash message is correct when add is cancelled."""
    prov = NuageProvider(parent=None, name=None)
    request.addfinalizer(prov.delete_if_exists)
    try:
        prov.create(cancel=True, validate_credentials=False)
    except MoveTargetOutOfBoundsException:
        # TODO: Remove once fixed 1475303
        prov.create(cancel=True, validate_credentials=False)
    view = prov.browser.create_view(NetworkProvidersView)
    view.flash.assert_success_message('Add of Network Manager was cancelled by the user')


def test_provider_add_with_bad_credentials(provider):
    """ Tests provider add with bad credentials

    Metadata:
        test_flag: crud
    """
    default_credentials = provider.default_endpoint.credentials

    # default settings
    flash = 'Login failed due to a bad username or password.'
    default_credentials.principal = "bad"
    default_credentials.secret = 'notyourday'

    with error.expected(flash):
        provider.create(validate_credentials=True)


@pytest.mark.smoke
def test_provider_create_new_then_delete(provider, has_no_networks_providers):
    """ Tests provider add with good credentials

    Metadata:
        test_flag: crud
    """
    provider.create()
    provider.validate_stats(ui=True)
    provider.delete(cancel=False)
    provider.wait_for_delete()
