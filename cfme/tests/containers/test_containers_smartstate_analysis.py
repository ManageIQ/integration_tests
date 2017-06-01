import dateparser
from collections import namedtuple

import pytest

from cfme.containers.image import Image
from cfme.containers.provider import ContainersProvider, ContainersTestItem,\
    navigate_and_get_rows

from utils import testgen
from utils.blockers import BZ
from utils.wait import wait_for
from cfme.configure.tasks import delete_all_tasks


pytestmark = [
    pytest.mark.meta(server_roles='+smartproxy'),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

AttributeToVerify = namedtuple('AttributeToVerify', ['table', 'attr', 'verifier'])

TESTED_ATTRIBUTES__openscap_off = (
    AttributeToVerify('configuration', 'openscap_results', bool),
    AttributeToVerify('configuration', 'openscap_html', lambda val: val == 'Available'),
    AttributeToVerify('configuration', 'last_scan', dateparser.parse)
)
TESTED_ATTRIBUTES__openscap_on = TESTED_ATTRIBUTES__openscap_off + (
    AttributeToVerify('compliance', 'status', lambda val: val.lower() != 'never verified'),
    AttributeToVerify('compliance', 'history', lambda val: val == 'Available')
)

TEST_ITEMS = (
    pytest.mark.polarion('CMP-9496')(
        ContainersTestItem(Image, 'CMP-9496',
                           is_openscap=False,
                           tested_attr=TESTED_ATTRIBUTES__openscap_off)
    ),
    pytest.mark.polarion('CMP-10064')(
        ContainersTestItem(Image, 'CMP-10064',
                           is_openscap=True,
                           tested_attr=TESTED_ATTRIBUTES__openscap_on)
    )
)


@pytest.fixture(scope='function')
def delete_all_container_tasks():
    delete_all_tasks('AllTasks')


@pytest.fixture(scope='function')
def random_image_instance(provider):
    chosen_row = navigate_and_get_rows(provider, Image, 1).pop()
    return Image(chosen_row.name.text, chosen_row.id.text, provider)


@pytest.mark.polarion('10030')
def test_manage_policies_navigation(random_image_instance):
    random_image_instance.assign_policy_profiles('OpenSCAP profile')


@pytest.mark.polarion('10031')
def test_check_compliance(random_image_instance):
    random_image_instance.assign_policy_profiles('OpenSCAP profile')
    random_image_instance.check_compliance()


@pytest.mark.meta(blockers=[BZ(1382326), BZ(1408255), BZ(1371896),
                            BZ(1447655, forced_streams=['5.7', '5.8', 'upstream'])])
@pytest.mark.parametrize(('test_item'), TEST_ITEMS)
def test_containers_smartstate_analysis(provider, test_item, soft_assert,
                                        delete_all_container_tasks,
                                        random_image_instance):

    if test_item.is_openscap:
        random_image_instance.assign_policy_profiles('OpenSCAP profile')
    else:
        random_image_instance.unassign_policy_profiles('OpenSCAP profile')

    random_image_instance.perform_smartstate_analysis(wait_for_finish=True)

    random_image_instance.summary.reload()
    for tbl, attr, verifier in test_item.tested_attr:

        table = getattr(random_image_instance.summary, tbl)

        if not soft_assert(hasattr(table, attr),
                '{} table has missing attribute \'{}\''.format(tbl, attr)):
            continue
        provider.refresh_provider_relationships()
        wait_for_retval = wait_for(lambda: getattr(table, attr).value,
                                   message='Trying to get attribute "{}" of table "{}"'.format(
                                       attr, tbl),
                                   fail_func=random_image_instance.summary.reload,
                                   delay=5, num_sec=120, silent_failure=True)
        if not wait_for_retval:
            soft_assert(False, 'Could not get attribute "{}" for "{}" table.'
                        .format(attr, tbl))
            continue
        value = wait_for_retval.out
        soft_assert(verifier(value),
            '{}.{} attribute has unexpected value ({})'.format(tbl, attr, value))
