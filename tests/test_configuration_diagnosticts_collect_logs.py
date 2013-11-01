import pytest


@pytest.fixture
def pg_diagnostics(cnf_configuration_pg):
    return cnf_configuration_pg.click_on_diagnostics()


@pytest.fixture
def pg_this_server_diagnostics(pg_diagnostics):
    return pg_diagnostics.click_on_current_server_tree_node()


@pytest.fixture
def pg_collect_logs(pg_this_server_diagnostics):
    return pg_this_server_diagnostics.click_on_collect_logs_tab()


@pytest.fixture
def pg_collect_logs_edit(pg_collect_logs):
    return pg_collect_logs.edit()


@pytest.mark.nondestructive
def test_touch_main_elements(pg_collect_logs):
    """ Touch elements

    This test touches all main elements that should be present
    """
    pg_collect_logs.depot_uri
    pg_collect_logs.server
    pg_collect_logs.server_status
    pg_collect_logs.last_log_collection
    pg_collect_logs.last_message

    assert pg_collect_logs.edit_button
    assert pg_collect_logs.collect_button


@pytest.mark.nondestructive
@pytest.mark.parametrize(("protocol", "credentials"),
                         [("ftp", dict(user="foo", password="bar", uri="doom")),
                          ("smb", dict(user="foo", password="bar", uri="doom")),
                          ("nfs", dict(uri="doom"))
                          ])
def test_enter_credentials(pg_collect_logs_edit, protocol, credentials):
    """ Enter credentials, validate and do not save

    This test enters provided credentials, validates them and then turns
    the log depot back off
    """
    uri = credentials["uri"]
    del credentials["uri"]
    pg_collect_logs_edit.fill_credentials(protocol, uri, **credentials)
    pg_collect_logs_edit.depot_type = None
