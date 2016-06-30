import pytest
from utils.appliance import ViaUI, ViaDB, current_appliance

from cfme.infrastructure.pxe import PXEServer


@pytest.fixture
def pxeserver():
    # ** So this fixture is just a dummy, we know the PXE server isn't going to be found
    # ** which is why the negative assertion is in the test body. This just was the first
    # ** method that we created using Sentaku.
    return PXEServer(name="John")


@pytest.mark.parametrize("endpoint", [ViaUI, ViaDB], ids=["ui", "db"])
def test_pxe_server_exist(endpoint, pxeserver):
    # ** Interesting things to note here is that we are able to parametrize the test
    # ** based on the endpoints. The test results actually look like this
    # **
    # ** collected 2 items
    # **
    # ** Appliance's streams: [5.6, downstream]
    # **    tmp/test_pxe_server.py::test_pxe_server_exist[ui]
    # **    tmp/test_pxe_server.py::test_pxe_server_exist[db]
    # **
    # ** tmp/test_pxe_server.py ..
    # ** This was one of the goals for FW3.0, to be able to take a test and without modifying
    # ** it specifically for an implementation, run it across multiple implementations. This
    # ** potentially makes life a lot easier. Write Once - Use Many testing means we can focus
    # ** more on expanding test coverage and let the framework handle the heavy lifting of running
    # ** it against multiple endpoints.

    # ** Full disclosure, we are not happy with the lines below. The intention is that this will
    # ** probably happen outside the test context. Meaning that we won't need to specify the context
    # ** in the body of the test. If we parametrize by an endpoint, then it will enforce that
    # ** endpoint and the test will fail if that endpoint is not used (ie if any method that has a
    # ** choice doesn't have the required choice for that test.

    # ** Notice pxeserver.exists() is not specifying any endpoint, this is being decided by Sentaku
    # ** at the context level.

    # ** The syntax is also too long, and you can read a comment in utils.appliance about renaming
    # ** this. sentaku_ctx is cryptic. endpoint_manager or something would be better. Remember y'all
    # ** this is WIP.
    with current_appliance.sentaku_ctx.use(endpoint):
        assert not pxeserver.exists()
