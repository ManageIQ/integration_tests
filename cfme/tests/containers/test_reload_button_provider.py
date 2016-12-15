import pytest

from cfme.containers.provider import ContainersProvider
from utils import testgen, version
from cfme.web_ui import toolbar as tb
from utils.appliance.implementations.ui import navigate_to


pytestmark = [
    pytest.mark.uncollectif(
        lambda: version.current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(2)]
pytest_generate_tests = testgen.generate([ContainersProvider], scope='function')

# CMP-9878


def test_reload_button_provider(provider):
    """ This test verifies the data integrity of the fields in
        the Relationships table after clicking the "reload"
        button. Fields that are being verified as part of provider.validate.stats():
        Projects, Routes, Container Services, Replicators, Pods, Containers, and Nodes.
        Images and Image Registries are being validated separately, since the total
        number of images in CFME 5.7 includes all images from the OSE registry as well
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

    for s in list_img_from_openshift_parsed:
        for item in list_img_from_registry_splitted:
            if item not in list_img_from_openshift_parsed:
                list_img_from_openshift_parsed.append(item)

    num_img_in_cfme = provider.summary.relationships.container_images.value
    assert len(list_img_from_openshift_parsed) == num_img_in_cfme

    list_all_rgstr = provider.mgmt.list_image_registry()
    list_all_rgstr_revised = [i.host for i in list_all_rgstr]
    list_all_rgstr_new = filter(lambda ch: 'openshift3' not in ch, list_all_rgstr_revised)

    num_rgstr_in_cfme = provider.summary.relationships.image_registries.value

    assert len(list_all_rgstr_new) == num_rgstr_in_cfme
