import pytest
from cfme.middleware import get_random_list
from cfme.middleware.messaging import MiddlewareMessaging
from utils import testgen
from utils.version import current_version
from deployment_methods import get_server
from deployment_methods import HAWKULAR_PRODUCT_NAME

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")
ITEMS_LIMIT = 1  # when we have big list, limit number of items to test


def test_list_messagings():
    """Tests messagings list between UI, DB and Management system
    This test requires that no any other provider should exist before.

    Steps:
        * Get messagings list from UI
        * Get messagings list from Database
        * Get messagings list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_msges = _get_messagings_set(MiddlewareMessaging.messagings())
    db_msges = _get_messagings_set(MiddlewareMessaging.messagings_in_db())
    mgmt_msges = _get_messagings_set(MiddlewareMessaging.messagings_in_mgmt())
    headers = MiddlewareMessaging.headers()
    headers_expected = ['Messaging Name', 'Messaging Type', 'Server']
    assert headers == headers_expected
    assert ui_msges == db_msges == mgmt_msges, \
        ("Lists of messagings mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_msges, db_msges, mgmt_msges))


def test_list_server_messagings(provider):
    """Gets servers list and tests messagings list for each server
    Steps:
        * Get Local server from UI of provider
        * Get messagings list from UI of server
        * Get messagings list from Database of server
        * Compare size of all the list [UI, Database]
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_msges = _get_messagings_set(MiddlewareMessaging.messagings(server=server))
    db_msges = _get_messagings_set(MiddlewareMessaging.messagings_in_db(server=server))
    assert ui_msges == db_msges, \
        ("Lists of messagings mismatch! UI:{}, DB:{}".format(ui_msges, db_msges))


def test_list_provider_messagings(provider):
    """Tests messagings list from current Provider between UI, DB and Management system

    Steps:
        * Get messagings list from UI of provider
        * Get messagings list from Database of provider
        * Get messagings list from Management system(Hawkular)
        * Compare size of all the list [UI, Database, Management system]
    """
    ui_msges = _get_messagings_set(MiddlewareMessaging.messagings(provider=provider))
    db_msges = _get_messagings_set(MiddlewareMessaging.messagings_in_db(provider=provider))
    mgmt_msges = _get_messagings_set(MiddlewareMessaging.messagings_in_mgmt(provider=provider))
    assert ui_msges == db_msges == mgmt_msges, \
        ("Lists of messagings mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_msges, db_msges, mgmt_msges))


def test_list_provider_server_messagings(provider):
    """Tests messagings list from current Provider for each server
    between UI, DB and Management system
    Steps:
        * Get Local server from UI of provider
        * Get messagings list for the server
        * Get messagings list from UI of provider, server
        * Get messagings list from Database of provider, server
        * Get messagings list from Database of provider, server
        * Get messagings list from Management system(Hawkular) of server
        * Compare size of all the list [UI, Database, Management system]
    """
    server = get_server(provider, HAWKULAR_PRODUCT_NAME)
    ui_msges = _get_messagings_set(
        MiddlewareMessaging.messagings(provider=provider, server=server))
    db_msges = _get_messagings_set(
        MiddlewareMessaging.messagings_in_db(provider=provider, server=server))
    mgmt_msges = _get_messagings_set(
        MiddlewareMessaging.messagings_in_mgmt(provider=provider, server=server))
    assert ui_msges == db_msges == mgmt_msges, \
        ("Lists of messagings mismatch! UI:{}, DB:{}, MGMT:{}"
         .format(ui_msges, db_msges, mgmt_msges))


def test_messaging_details(provider):
    """Tests messaging details on UI

    Steps:
        * Get messagings list from UI
        * Select each messaging details in UI
        * Compare selected messaging UI details with CFME database
    """
    msg_list = MiddlewareMessaging.messagings(provider=provider)
    for msg in get_random_list(msg_list, ITEMS_LIMIT):
        msg_ui = msg.messaging(method='ui')
        msg_db = msg.messaging(method='db')
        assert msg_ui, "Messaging was not found in UI"
        assert msg_db, "Messaging was not found in DB"
        assert msg_ui.name == msg_db.name, \
            ("messaging name does not match between UI:{}, DB:{}"
             .format(msg_ui.name, msg_db.name))
        msg_db.validate_properties()


def _get_messagings_set(messagings):
    """
    Return the set of messagings which contains only necessary fields,
    such as 'name', 'type' and 'server'
    """
    return set((messaging.name, messaging.messaging_type, messaging.server.name)
               for messaging in messagings)
