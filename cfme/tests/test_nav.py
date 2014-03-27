import pytest

from cfme.web_ui import menu


def pytest_generate_tests(metafunc):
    argnames = ['nav_dest']
    argvalues = []
    idlist = []
    for (nav_dest, toplevel_name), secondlevels in menu.sections.items():
        argvalues.append([nav_dest])
        idlist.append(toplevel_name)
        for nav_dest, secondlevel_name in secondlevels:
            argvalues.append([nav_dest])
            idlist.append('%s/%s' % (toplevel_name, secondlevel_name))
    metafunc.parametrize(argnames, argvalues, ids=idlist)


@pytest.mark.smoke
def test_nav_destination(nav_dest):
    pytest.sel.force_navigate(nav_dest)
