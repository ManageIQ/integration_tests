import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.service import Service
from utils import testgen
from utils.version import current_version
from cfme.web_ui import CheckboxTable

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")


# Polarion test case CMP-9884
# container services verification
@pytest.mark.parametrize('rel',
                         ['Name',
                          'Creation timestamp',
                          'Resource version',
                          'Session affinity',
                          'Type',
                          'Portal IP'])
def test_service_summary_rel(provider, rel):
    sel.force_navigate('containers_services')
    list_tbl_service = CheckboxTable(
        table_locator="//div[@id='list_grid']//table")
    ui_services = [r.name.text for r in list_tbl_service.rows()]
    mgmt_objs = provider.mgmt.list_service()  # run only if table is not empty
    validate_str = False

    if ui_services:
        # verify that mgmt services exist in ui listed services
        assert set(ui_services).issubset(
            [obj.name for obj in mgmt_objs]), 'Missing objects'

    for name in ui_services:
        obj = Service(name, provider)
        val = obj.get_detail('Properties', rel)

        # the field should not be empty
        try:
            str(val)
            validate_str = True
        except ValueError:
            pass

        if validate_str:
            assert len(val) != 0
