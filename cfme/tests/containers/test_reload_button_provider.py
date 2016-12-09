import pytest

from utils.appliance.implementations.ui import navigate_to
from cfme.containers.provider import ContainersProvider
from utils import testgen, version
from utils.version import current_version
from cfme.web_ui import toolbar as tb

pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

# CMP-9878


def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button. Fields that are being verified as part of provider.validate.stats():
        Projects, Routes, Container Services, Replicators, Pods, Containers, Nodes,
        and Image Registries. Images are being verified separately, since the total
        number of images in CFME 5.7 includes all images from the registry as well
        as the images that are being created from the running pods

    """

    navigate_to(ContainersProvider, 'All')
    provider.load_details()
    tb.select('Reload Current Display')
    provider.validate_stats(ui=True)

    num_img_from_registry = len(provider.mgmt.o_api.get('image')[1]['items'])
    num_img_from_openshift = len(provider.mgmt.list_image())

    num_img_api_list = num_img_from_registry + num_img_from_openshift
    num_img_ui = provider.num_image()

    if version.current_version() < "5.7":
        assert num_img_ui == num_img_from_openshift
    else:
        assert num_img_api_list == num_img_ui
