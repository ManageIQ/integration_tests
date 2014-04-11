import pytest

from cfme.web_ui import menu


def pytest_generate_tests(metafunc):
    argnames = ['nav_dest']
    argvalues = []
    for (nav_dest, toplevel_name), secondlevels in menu.sections.items():
        argvalues.append([nav_dest])
        for nav_dest, secondlevel_name in secondlevels:
            argvalues.append([nav_dest])
    metafunc.parametrize(argnames, sorted(argvalues))


@pytest.mark.smoke
def test_nav_destination(nav_dest):
    pytest.sel.force_navigate(nav_dest)
