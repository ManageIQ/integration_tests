import pytest
from unittestzero import Assert

from utils.conf import cfme_data
from utils.providers import infra_provider_type_map, setup_infrastructure_provider
from utils.wait import wait_for

CURRENT_PAGE_NOT_MATCHED = 'Current page not what was expected'
FLASH_MESSAGE_NOT_MATCHED = 'Flash message did not match expected value'
DETAIL_NOT_MATCHED_TEMPLATE = '%s did not match'


def pytest_generate_tests(metafunc):
    if 'provider_data' in metafunc.fixturenames:
        funcargs = dict()
        for provider, provider_data in cfme_data['management_systems'].items():
            if provider_data['type'] not in infra_provider_type_map:
                continue

            value = provider_data.copy()
            value['request'] = provider
            funcargs[provider] = value

        metafunc.parametrize('provider_data', funcargs.values(), ids=funcargs.keys())


@pytest.yield_fixture
def provider(request, provider_data, db_session):
    '''Create a management system

    Creates a management system based on the data from cfme_data.
    Ideally, this fixture would clean up after itself, but currently
    the only way to do that is via the UI, and we lose the selenium session
    before the finalizer gets an opportunity to run.

    This fixture will modify the db directly in the near future'''
    setup_infrastructure_provider(provider_data['request'], provider_data)
    yield provider_data
    has_no_providers(db_session)


@pytest.fixture
def has_no_providers(db_session):
    '''Clears all management systems from an applicance

    This is a destructive fixture. It will clear all managements systems from
    the current appliance.
    '''
    import db
    session = db_session
    session.query(db.ExtManagementSystem).delete()
    session.commit()


def test_that_checks_flash_with_no_provider_types_checked(infra_providers_pg):
    prov_pg = infra_providers_pg
    Assert.true(prov_pg.is_the_current_page)
    prov_discover_pg = prov_pg.click_on_discover_providers()
    prov_discover_pg.click_on_start()
    Assert.equal(prov_discover_pg.flash.message,
            'At least 1 item must be selected for discovery',
            FLASH_MESSAGE_NOT_MATCHED)


def test_that_checks_flash_when_discovery_cancelled(infra_providers_pg):
    prov_pg = infra_providers_pg
    Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
    prov_discover_pg = prov_pg.click_on_discover_providers()
    prov_pg = prov_discover_pg.click_on_cancel()
    Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
    Assert.equal(prov_pg.flash.message,
            'Infrastructure Providers Discovery was cancelled by the user',
            FLASH_MESSAGE_NOT_MATCHED)


def test_that_checks_flash_when_add_cancelled(infra_providers_pg):
    prov_pg = infra_providers_pg
    Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
    prov_add_pg = prov_pg.click_on_add_new_provider()
    prov_pg = prov_add_pg.click_on_cancel()
    Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
    Assert.equal(prov_pg.flash.message,
        'Add of new Infrastructure Provider was cancelled by the user',
        FLASH_MESSAGE_NOT_MATCHED)


@pytest.mark.usefixtures('has_no_providers')
def test_providers_discovery_starts(infra_providers_pg, provider_data):
    prov_pg = infra_providers_pg
    Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
    prov_discovery_pg = prov_pg.click_on_discover_providers()
    Assert.true(prov_discovery_pg.is_the_current_page,
        CURRENT_PAGE_NOT_MATCHED)
    prov_pg = prov_discovery_pg.discover_infrastructure_providers(
        provider_data['type'],
        provider_data['discovery_range']['start'],
        provider_data['discovery_range']['end']
    )
    Assert.true(prov_pg.is_the_current_page, CURRENT_PAGE_NOT_MATCHED)
    Assert.equal(prov_pg.flash.message,
        'Infrastructure Providers: Discovery successfully initiated',
        FLASH_MESSAGE_NOT_MATCHED)
    wait_for(prov_pg.is_quad_icon_available, [provider_data['default_name']])


@pytest.mark.usefixtures('has_no_providers')
def test_provider_edit(infra_providers_pg, provider, random_string):
    prov_pg = infra_providers_pg
    prov_pg.taskbar_region.view_buttons.change_to_grid_view()
    Assert.true(prov_pg.taskbar_region.view_buttons.is_grid_view)
    prov_pg.select_provider(provider['name'])
    Assert.equal(len(prov_pg.quadicon_region.selected), 1,
        'More than one quadicon was selected')
    prov_edit_pg = prov_pg.click_on_edit_providers()
    provider['name'] = random_string
    prov_edit_pg.fill_provider(provider)
    prov_edit_pg.click_on_reset()
    Assert.equal(prov_edit_pg.flash.message,
        'All changes have been reset',
        FLASH_MESSAGE_NOT_MATCHED)
    prov_detail_pg = prov_edit_pg.edit_provider(provider)
    Assert.equal(prov_detail_pg.flash.message,
        'Infrastructure Provider "%s" was saved' % provider['name'],
        FLASH_MESSAGE_NOT_MATCHED)
    Assert.equal(prov_detail_pg.name, provider['name'],
        DETAIL_NOT_MATCHED_TEMPLATE % 'Edited name')
    Assert.equal(prov_detail_pg.hostname, provider['hostname'],
        DETAIL_NOT_MATCHED_TEMPLATE % 'Hostname')
    Assert.equal(prov_detail_pg.zone, provider['server_zone'],
        DETAIL_NOT_MATCHED_TEMPLATE % 'Server zone')
    if 'host_vnc_port' in provider:
        Assert.equal(prov_detail_pg.vnc_port_range,
            provider['host_vnc_port'],
            DETAIL_NOT_MATCHED_TEMPLATE % 'VNC port range')


@pytest.mark.usefixtures('has_no_providers')
def test_provider_add(infra_providers_pg, provider_data):
    prov_pg = infra_providers_pg
    prov_add_pg = prov_pg.click_on_add_new_provider()
    prov_pg = prov_add_pg.add_provider(provider_data)
    Assert.equal(prov_pg.flash.message,
        'Infrastructure Providers "%s" was saved' % provider_data['name'],
        FLASH_MESSAGE_NOT_MATCHED)
    prov_pg.wait_for_provider_or_timeout(provider_data)


@pytest.mark.usefixtures('has_no_providers')
def test_provider_add_with_bad_credentials(infra_providers_pg, provider_data):
    prov_pg = infra_providers_pg
    prov_add_pg = prov_pg.click_on_add_new_provider()
    provider_data['credentials'] = 'bad_credentials'
    prov_add_pg.fill_provider_with_bad_credentials(provider_data)
    Assert.false(prov_add_pg.validate())
