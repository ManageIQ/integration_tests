import pytest


@pytest.fixture
def pg_diagnostics(cnf_configuration_pg):
    return cnf_configuration_pg.click_on_diagnostics()


@pytest.fixture
def pg_this_server_diagnostics(pg_diagnostics):
    return pg_diagnostics.click_on_current_server_tree_node()


@pytest.fixture
def pg_workers_diagnostics(pg_this_server_diagnostics):
    return pg_this_server_diagnostics.click_on_workers_tab()


def test_restart_ui_workers(pg_workers_diagnostics):
    pg_workers_diagnostics.restart_workers_by_name("User Interface Worker")
