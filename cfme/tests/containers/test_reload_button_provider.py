import pytest

from utils import testgen, version
from cfme.web_ui import toolbar as tb
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope='function')

# CMP-9878


def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button. Fields that are being verified as part of provider.validate.stats():
        Projects, Routes, Container Services, Replicators, Pods, Containers, and Nodes.
        Images are being verified separately, since the total
        number of images in CFME 5.7 includes all images from the OSE registry as well
        as the images that are being created from the running pods. The images are searched
        according to the @sha.

    """

    navigate_to(provider, 'Details')
    tb.select('Reload Current Display')
    provider.validate_stats(ui=True)

    l1 = provider.mgmt.list_image()

    l1splitted = [i[2].split('@sha256:')[-1] for i in l1]

    l2 = provider.mgmt.list_image_openshift()

    l2splitted = [d['name'] for d in l2]

    l2splitted_new = [i[7:].split('@sha256:')[-1] for i in l2splitted]

    for s in l2splitted_new:
        for item in l1splitted:
            if item not in l2splitted_new:
                l2splitted_new.append(item)

    num_img_in_cfme = provider.summary.relationships.container_images.value

    assert len(l2splitted_new) == num_img_in_cfme
