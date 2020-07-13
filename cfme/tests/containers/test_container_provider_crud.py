import fauxfactory
import pytest

from cfme import test_requirements
from cfme.common.provider_views import ContainerProvidersView
from cfme.containers.provider import ContainersProvider
from cfme.markers.env_markers.provider import ONE_PER_VERSION
from cfme.utils.rest import assert_response
from cfme.utils.update import update


pytestmark = [
    pytest.mark.tier(1),
    test_requirements.containers,
    pytest.mark.provider(
        [ContainersProvider],
        scope='function',
        selector=ONE_PER_VERSION),
]


@pytest.mark.meta(automates=[1763857])
def test_container_provider_crud(request, appliance, has_no_providers, provider):

    """
    Polarion:
        assignee: juwatts
        caseimportance: critical
        casecomponent: Containers
        initialEstimate: 1/6h

    Bugzilla:
        1763857
    """

    provider.create()

    request.addfinalizer(lambda: provider.delete_if_exists(cancel=False))

    view = appliance.browser.create_view(ContainerProvidersView)

    view.flash.assert_success_message('{} Providers "{}" was saved'.format(provider.string_name,
                                                                           provider.name))

    assert provider.exists

    with update(provider):
        provider.name = fauxfactory.gen_alpha(8).lower()

    assert view.is_displayed

    view.flash.assert_success_message(
        f'Containers Provider "{provider.name}" was saved')

    assert provider.name == str(view.entities.get_first_entity().data.get('name', {}))

    provider.delete()

    assert view.is_displayed

    view.flash.assert_success_message('Delete initiated for 1 {} Provider from '
                                      'the {} Database'.format(provider.string_name,
                                                               appliance.product_name))

    provider.wait_for_delete()

    assert not provider.exists


@test_requirements.rest
def test_container_provider_crud_rest(appliance, has_no_providers, provider):
    """
    Test
    Polarion:
        assignee: pvala
        caseimportance: critical
        casecomponent: Containers
        initialEstimate: 1/6h
    """
    provider.create_rest()
    provider_rest = appliance.rest_api.collections.providers.get(name=provider.name)
    assert provider_rest.type == "ManageIQ::Providers::Openshift::ContainerManager"

    new_name = fauxfactory.gen_alphanumeric()
    edited = provider_rest.action.edit(name=new_name)
    assert_response(appliance)
    provider_rest.reload()
    assert provider_rest.name == new_name == edited.name

    provider_rest.action.delete()
    provider_rest.wait_not_exists()

    assert not provider_rest.exists
