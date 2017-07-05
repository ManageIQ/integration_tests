from __future__ import absolute_import
import pytest

from cfme.containers.provider import ContainersProvider
from cfme.web_ui import toolbar as tb
from utils import testgen, version
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')


@pytest.mark.polarion('CMP-9878')
@pytest.mark.skip(reason="This test is currently skipped due to instability issues. ")
def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button. Fields that are being verified as part of provider.validate.stats():
        Projects, Routes, Container Services, Replicators, Pods, Image Registries,
        Containers, and Nodes.
        Images are being validated separately, since the total
        number of images in CFME 5.7 and CFME 5.8 includes all images from the OSE registry as well
        as the images that are being created from the running pods. The images are searched
        according to the @sha.
    """

    navigate_to(provider, 'Details')
    tb.select('Reload Current Display')
    provider.validate_stats(ui=True)

    list_img_from_registry = provider.mgmt.list_image()
    list_img_from_registry_splitted = [i.id.split(
        '@sha256:')[-1] for i in list_img_from_registry]

    list_img_from_openshift = provider.mgmt.list_image_openshift()
    list_img_from_openshift_splitted = [d['name']
                                        for d in list_img_from_openshift]
    list_img_from_openshift_parsed = [i[7:].split(
        '@sha256:')[-1] for i in list_img_from_openshift_splitted]
    list_img_from_registry_splitted_new = set(list_img_from_registry_splitted)
    list_img_from_openshift_parsed_new = set(list_img_from_openshift_parsed)

    list_img_from_openshift_parsed_new.update(list_img_from_registry_splitted_new)

    num_img_in_cfme = provider.num_image()
    # TODO Fix num_image_ui()

    num_img_cfme_56 = len(provider.mgmt.list_image())
    num_img_cfme_57 = len(list_img_from_openshift_parsed_new)

    assert num_img_in_cfme == version.pick({version.LOWEST: num_img_cfme_56,
                                            '5.7': num_img_cfme_57})
