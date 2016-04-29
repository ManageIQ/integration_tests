from cfme.middleware.server import Server

from utils import testgen


def pytest_generate_tests(metafunc):
    # Filter out providers without provisioning data or hosts defined
    argnames, argvalues, idlist = testgen.middleware_providers(metafunc)
    testgen.parametrize(
        metafunc, argnames, argvalues, ids=idlist, scope="module")


def test_server_details(provider, setup_provider):

    server = Server(provider.name, provider)
    server.nav_to_detailed_view()

    assert False, "Server Details Validation - To Do"
