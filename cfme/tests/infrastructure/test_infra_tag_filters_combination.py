import fauxfactory
import pytest

from cfme import test_requirements
from cfme.infrastructure.cluster import Cluster
from cfme.configure.access_control import User
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.infrastructure.virtual_machines import Vm, Template
from cfme.web_ui import mixins
from fixtures.provider import setup_one_or_skip
from utils.appliance.implementations.ui import navigate_to
from utils.log import logger
from utils.providers import ProviderFilter
from utils.update import update


pytestmark = [test_requirements.tag, pytest.mark.tier(2)]


@pytest.fixture(scope='module')
def a_provider(request):
    prov_filter = ProviderFilter(classes=[VMwareProvider])
    return setup_one_or_skip(request, filters=[prov_filter])


@pytest.fixture(scope='function')
def cluster(a_provider):
    clusters = a_provider.get_clusters()
    if not clusters:
        pytest.skip('No content found for test!')
    return Cluster(name=clusters[0].name, provider=a_provider)


@pytest.fixture(scope='function')
def vm(a_provider):
    vms_list = a_provider.mgmt.list_vm()
    return Vm(vms_list[0], a_provider)


@pytest.fixture(scope='function')
def template(a_provider):
    templates_list = a_provider.mgmt.list_template()
    return Template(templates_list[0], a_provider)


@pytest.yield_fixture(scope='function')
def restricted_user(group, new_credential):
    user = User(
        name='user' + fauxfactory.gen_alphanumeric(),
        credential=new_credential,
        email='xyz@redhat.com',
        group=group)
    user.create()
    yield user
    user.delete()


@pytest.fixture(scope='function')
def check_item_visibility(tag, user_restricted):
    def _check_item_visibility(visibility_result, testing_vis_object):
        """
        Args:
            visibility_result: pass 'True' is item should be visible,
                               'False' if not
        """
        navigate_to(testing_vis_object, 'Details')
        if visibility_result:
            mixins.add_tag(tag)
        else:
            mixins.remove_tag(tag)
        with user_restricted:
            try:
                navigate_to(testing_vis_object, 'Details')
                actual_visibility = True
            except Exception:
                logger.debug('Tagged item is not visible')
                actual_visibility = False
        assert actual_visibility == visibility_result
    return _check_item_visibility


def test_tagvis_tag_cluster_combination(a_provider, group, cluster, check_item_visibility,
                                        category, tag):
    """ Tests cluster visibility with combination of tag and cluster filters in the group
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag
        2. Login as restricted user, item is visible for user
        3. As admin remove tag
        4. Login as restricted user, item is not visible for user
    """
    # Admin adds a tag, user should see item

    with update(group):
        group.tag = [category.display_name, tag.display_name]
        group.vm_template = [a_provider.data['name'], a_provider.data['datacenters'][0],
                             'Discovered virtual machine']
    check_item_visibility(True, cluster)
    # Admin removes a tag, user should not see item
    check_item_visibility(False, cluster)


def test_tagvis_tag_vm_combination(vm, group, category, tag, a_provider, check_item_visibility):
    """ Tests vm visibility with combination of tag and datacenter filters in the group
      Prerequisites:
          Catalog, tag, role, group and restricted user should be created

      Steps:
          1. As admin add tag
          2. Login as restricted user, item is visible for user
          3. As admin remove tag
          4. Login as restricted user, iten is not visible for user
      """
    with update(group):
        group.tag = [category.display_name, tag.display_name]
        group.vm_template = [a_provider.data['name'], a_provider.data['datacenters'][0],
                             'Discovered virtual machine']
    # Admin adds a tag, user should see item
    check_item_visibility(True, vm)
    # Admin removes a tag, user should not see item
    check_item_visibility(False, vm)


@pytest.mark.parametrize("test", [vm, template], ids=['vm', 'template'])
def test_tagvis_tag_template_combination(test, group, category, tag,
                                         a_provider, check_item_visibility):
    """ Tests template visibility with combination of tag and selected
        datacenter filters in the group
         Prerequisites:
             Catalog, tag, role, group and restricted user should be created

         Steps:
             1. As admin add tag
             2. Login as restricted user, item is visible for user
             3. As admin remove tag
             4. Login as restricted user, iten is not visible for user
         """
    with update(group):
        group.tag = [category.display_name, tag.display_name]
        group.vm_template = [a_provider.data['name'], a_provider.data['datacenters'][0],
                             'Discovered virtual machine']
    # Admin adds a tag, user should see item
    check_item_visibility(True, test)
    # Admin removes a tag, user should not see item
    check_item_visibility(False, test)
