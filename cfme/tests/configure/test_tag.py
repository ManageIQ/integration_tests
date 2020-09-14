import tempfile

import fauxfactory
import pytest

from cfme import test_requirements
from cfme.cloud.provider import CloudProvider
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.markers.env_markers.provider import ONE_PER_CATEGORY
from cfme.rest.gen_data import categories as _categories
from cfme.rest.gen_data import service_templates as _service_templates
from cfme.rest.gen_data import tags as _tags
from cfme.rest.gen_data import tenants as _tenants
from cfme.rest.gen_data import users as _users
from cfme.rest.gen_data import vm as _vm
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.update import update
from cfme.utils.wait import wait_for


CLOUD_COLLECTION = [
    "availability_zones",
    "cloud_networks",
    "cloud_subnets",
    "flavors",
    "network_routers",
    "security_groups",
]
INFRA_COLLECTION = [
    "clusters",
    "hosts",
    "data_stores",
    "providers",
    "resource_pools",
    "services",
    "service_templates",
    "tenants",
    "vms",
    "users",
]
pytestmark = [
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture
def category(appliance):
    cg = appliance.collections.categories.create(
        name=fauxfactory.gen_alphanumeric(8).lower(),
        description=fauxfactory.gen_alphanumeric(32),
        display_name=fauxfactory.gen_alphanumeric(32)
    )
    yield cg
    if cg.exists:
        cg.delete()


@pytest.fixture
def tag(category):
    tag = category.collections.tags.create(
        name=fauxfactory.gen_alphanumeric(8).lower(),
        display_name=fauxfactory.gen_alphanumeric(32)
    )
    yield tag

    tag.delete_if_exists()


@pytest.mark.sauce
@pytest.mark.tier(2)
@test_requirements.tag
def test_tag_crud(tag):
    """
    Polarion:
        assignee: anikifor
        initialEstimate: 1/8h
        casecomponent: Tagging
    """
    assert tag.exists

    tag.update({
        'name': fauxfactory.gen_alphanumeric(8).lower(),
        'display_name': fauxfactory.gen_alphanumeric(32)
    })


@test_requirements.tag
def test_map_tagging_crud(appliance, category, soft_assert):
    """Test map tag crud with flash message assertion
    Polarion:
        assignee: anikifor
        initialEstimate: 1/4h
        casecomponent: Tagging
    Bugzilla:
        1707328
    """
    label = fauxfactory.gen_alphanumeric(8)
    map_tags_collection = appliance.collections.map_tags
    map_tag_entity = map_tags_collection.create('Container Project', label, category.name)

    view = appliance.browser.create_view(navigator.get_class(map_tags_collection, 'All').VIEW)
    view.flash.assert_success_message('Container Label Tag Mapping "{}" was added'
                                      .format(label))  # use label var to validate create method

    with update(map_tag_entity):
        map_tag_entity.category = fauxfactory.gen_alphanumeric(8)

    view = appliance.browser.create_view(navigator.get_class(map_tags_collection, 'All').VIEW)
    view.flash.assert_success_message(
        'Container Label Tag Mapping "{}" was saved'
        .format(map_tag_entity.label)  # use entity label since it may get updated
    )
    row = next(view.table.rows(resource_label=map_tag_entity.label))
    soft_assert(row.tag_category.text == map_tag_entity.category)

    map_tag_entity.delete()
    view = appliance.browser.create_view(navigator.get_class(map_tags_collection, 'All').VIEW)
    if appliance.version >= "5.11":  # BZ 1707328 is fixed only for 5.11
        view.flash.assert_success_message('Container Label Tag Mapping "{}": Delete successful'
                                          .format(map_tag_entity.label))


@pytest.fixture
def csv_tag_file(create_vm, category, tag):
    temp_file = tempfile.NamedTemporaryFile(suffix=".csv")
    csv_data = f'name,category,entry\n{create_vm.name},{category.display_name},{tag.display_name}'
    with open(temp_file.name, "w") as file:
        file.write(csv_data)
    yield file.name


@test_requirements.tag
def test_import_tag(appliance, create_vm, category, tag, csv_tag_file):
    """Test importing tag via file
            1. Create a Tag Category
            2. Create entry(tag) in the tag category
            3. Create a VM
            4. Create a CSV File for adding the tag to the VM
            5. Navigate to Tags -> Import tags and upload the CSV file
    Polarion:
        assignee: prichard
        initialEstimate: 1/4h
        casecomponent: Tagging
    Bugzilla:
        1792185
    """
    category.import_tag_from_file(csv_tag_file)
    # assert the tag is correctly assigned
    vm_tags = create_vm.get_tags()
    assert any(
        tag.category.display_name == vm_tag.category.display_name and
        tag.display_name == vm_tag.display_name
        for vm_tag in vm_tags
    ), "tag is not assigned"


@test_requirements.tag
def test_updated_tag_name_on_vm(provider, tag, request):
    """
    This test checks that tags don't disappear from the UI after their name (not displayed name) is
    changed.

    Bugzilla:
        1668730

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: high
        initialEstimate: 1/8h
        testSteps:
            1. create a tag
            2. assign the tag to some vm, observe the tag in Smart Management section of vm
            3. change name of the tag
            4. on VM screen: still the same tag in Smart Management section of vm
    """
    coll = provider.appliance.provider_based_collection(provider, coll_type='vms')
    # need some VM to assign tags to, nothing specific is needed, so take the first one
    vm = coll.all()[0]
    vm.add_tag(tag)
    request.addfinalizer(lambda: vm.remove_tag(tag))

    # assert the tag is correctly assigned
    vm_tags = vm.get_tags()
    assert any(
        tag.category.display_name == vm_tag.category.display_name and
        tag.display_name == vm_tag.display_name
        for vm_tag in vm_tags
    ), "tag is not assigned"

    # update the name of the tag
    new_tag_name = '{}_{}'.format(tag.name, fauxfactory.gen_alphanumeric(4).lower())
    tag.update({'name': new_tag_name})

    vm_tags = vm.get_tags()

    # assert the tag was not changed in the UI
    assert any(
        tag.category.display_name == vm_tag.category.display_name and
        tag.display_name == vm_tag.display_name
        for vm_tag in vm_tags
    ), 'tag is not assigned'


@test_requirements.rest
class TestTagsViaREST:

    COLLECTIONS_BULK_TAGS = ("services", "vms", "users")

    def _service_body(self, **kwargs):
        uid = fauxfactory.gen_alphanumeric(5)
        body = {
            'name': f'test_rest_service_{uid}',
            'description': f'Test REST Service {uid}',
        }
        body.update(kwargs)
        return body

    def _create_services(self, request, rest_api, num=3):
        # create simple service using REST API
        bodies = [self._service_body() for __ in range(num)]
        collection = rest_api.collections.services
        new_services = collection.action.create(*bodies)
        assert_response(rest_api)
        new_services_backup = list(new_services)

        @request.addfinalizer
        def _finished():
            collection.reload()
            ids = [service.id for service in new_services_backup]
            delete_entities = [service for service in collection if service.id in ids]
            if delete_entities:
                collection.action.delete(*delete_entities)

        return new_services

    @pytest.fixture(scope="function")
    def services(self, request, appliance):
        return self._create_services(request, appliance.rest_api)

    @pytest.fixture(scope="function")
    def categories(self, request, appliance, num=3):
        return _categories(request, appliance, num)

    @pytest.fixture(scope="function")
    def tags(self, request, appliance, categories):
        return _tags(request, appliance, categories)

    @pytest.fixture(scope="module")
    def services_mod(self, request, appliance):
        return self._create_services(request, appliance.rest_api)

    @pytest.fixture(scope="module")
    def categories_mod(self, request, appliance, num=3):
        return _categories(request, appliance, num)

    @pytest.fixture(scope="module")
    def tags_mod(self, request, appliance, categories_mod):
        return _tags(request, appliance, categories_mod)

    @pytest.fixture(scope="module")
    def tenants(self, request, appliance):
        return _tenants(request, appliance, num=1)

    @pytest.fixture(scope="module")
    def service_templates(self, request, appliance):
        return _service_templates(request, appliance)

    @pytest.fixture(scope="function")
    def vm(self, request, provider, appliance):
        return _vm(request, provider, appliance)

    @pytest.fixture(scope="function")
    def users(self, request, appliance, num=3):
        return _users(request, appliance, num=num)

    @pytest.mark.tier(2)
    def test_edit_tags_rest(self, appliance, tags):
        """Tests tags editing from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/6h
        """
        collection = appliance.rest_api.collections.tags
        tags_len = len(tags)
        tags_data_edited = []
        for tag in tags:
            tags_data_edited.append({
                "href": tag.href,
                "name": fauxfactory.gen_alphanumeric(15, start="test_tag_").lower(),
            })
        edited = collection.action.edit(*tags_data_edited)
        assert_response(appliance, results_num=tags_len)
        for index in range(tags_len):
            record, _ = wait_for(lambda:
                collection.find_by(name="%/{}".format(tags_data_edited[index]["name"])) or False,
                num_sec=180,
                delay=10)
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

    @pytest.mark.tier(2)
    def test_edit_tag_from_detail(self, appliance, tags):
        """Tests tag editing from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/30h
        """
        edited = []
        new_names = []
        for tag in tags:
            new_name = fauxfactory.gen_alphanumeric(15, start="test_tag_").lower()
            new_names.append(new_name)
            edited.append(tag.action.edit(name=new_name))
            assert_response(appliance)
        for index, name in enumerate(new_names):
            record, _ = wait_for(lambda:
                appliance.rest_api.collections.tags.find_by(name=f"%/{name}") or False,
                num_sec=180,
                delay=10)
            assert record[0].id == edited[index].id
            assert record[0].name == edited[index].name

    @pytest.mark.tier(3)
    @pytest.mark.parametrize("method", ["post", "delete"], ids=["POST", "DELETE"])
    def test_delete_tags_from_detail(self, tags, method):
        """Tests deleting tags from detail.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/30h
        """
        delete_resources_from_detail(tags, method=method)

    @pytest.mark.tier(3)
    def test_delete_tags_from_collection(self, tags):
        """Tests deleting tags from collection.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/30h
        """
        delete_resources_from_collection(tags, not_found=True)

    @pytest.mark.tier(3)
    def test_create_tag_with_wrong_arguments(self, appliance):
        """Tests creating tags with missing category "id", "href" or "name".

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/30h
        """
        data = {
            "name": fauxfactory.gen_alphanumeric(15, start="test_tag_").lower(),
            "description": fauxfactory.gen_alphanumeric(20, start="test_tag_desc_").lower()
        }
        msg = "BadRequestError: Category id, href or name needs to be specified"
        with pytest.raises(Exception, match=msg):
            appliance.rest_api.collections.tags.action.create(data)
        assert_response(appliance, http_status=400)

    @pytest.mark.tier(3)
    @pytest.mark.provider(
        [CloudProvider, InfraProvider], selector=ONE_PER_CATEGORY
    )
    @pytest.mark.parametrize("collection_name", INFRA_COLLECTION + CLOUD_COLLECTION)
    @pytest.mark.uncollectif(
        lambda appliance, collection_name, provider:
            (provider.one_of(CloudProvider) and collection_name in INFRA_COLLECTION) or
            (provider.one_of(InfraProvider) and collection_name in CLOUD_COLLECTION),
        reason='Invalid combination of provider type and collection name'
    )
    def test_assign_and_unassign_tag(self, appliance, tags_mod, provider, services_mod,
            service_templates, tenants, vm, collection_name, users):
        """Tests assigning and unassigning tags.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/5h
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        if not collection.all:
            pytest.skip(f"No available entity in {collection_name} to assign tag")
        entity = collection[-1]
        tag = tags_mod[0]
        try:
            entity.tags.action.assign(tag)
        except AttributeError:
            msg = ('Missing tag attribute in parametrized REST collection {} for entity: {}'
                   .format(collection_name, entity))
            logger.exception(msg)
            pytest.fail(msg)
        assert_response(appliance)
        entity.reload()
        assert tag.id in [t.id for t in entity.tags.all]
        entity.tags.action.unassign(tag)
        assert_response(appliance)
        entity.reload()
        assert tag.id not in [t.id for t in entity.tags.all]

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_tag(self, appliance, tags_mod, services_mod, vm,
            collection_name, users):
        """Tests bulk assigning and unassigning tags.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/5h
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        entities = collection.all[-2:]

        new_tags = []
        for index, tag in enumerate(tags_mod):
            identifiers = [{'href': tag._href}, {'id': tag.id}]
            new_tags.append(identifiers[index % 2])

        # add some more tags in supported formats
        new_tags.append({'category': 'department', 'name': 'finance'})
        new_tags.append({'name': '/managed/department/presales'})
        tags_ids = {t.id for t in tags_mod}
        tags_ids.add(
            appliance.rest_api.collections.tags.get(name='/managed/department/finance').id)
        tags_ids.add(
            appliance.rest_api.collections.tags.get(name='/managed/department/presales').id)
        tags_count = len(new_tags) * len(entities)

        response = collection.action.assign_tags(*entities, tags=new_tags)
        assert_response(appliance, results_num=tags_count)

        # testing BZ 1460257
        results = appliance.rest_api.response.json()['results']
        entities_hrefs = [e.href for e in entities]
        for result in results:
            assert result['href'] in entities_hrefs

        for index, entity in enumerate(entities):
            entity.tags.reload()
            response[index].id = entity.id
            assert tags_ids.issubset({t.id for t in entity.tags.all})

        collection.action.unassign_tags(*entities, tags=new_tags)
        assert_response(appliance, results_num=tags_count)
        for entity in entities:
            entity.tags.reload()
            assert len({t.id for t in entity.tags.all} - tags_ids) == entity.tags.subcount

    @pytest.mark.tier(3)
    @pytest.mark.parametrize(
        "collection_name", COLLECTIONS_BULK_TAGS)
    def test_bulk_assign_and_unassign_invalid_tag(self, appliance, services_mod, vm,
            collection_name, users):
        """Tests bulk assigning and unassigning invalid tags.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/5h
        """
        collection = getattr(appliance.rest_api.collections, collection_name)
        collection.reload()
        entities = collection.all[-2:]

        new_tags = ['invalid_tag1', 'invalid_tag2']
        tags_count = len(new_tags) * len(entities)
        tags_per_entities_count = []
        for entity in entities:
            entity.tags.reload()
            tags_per_entities_count.append(entity.tags.subcount)

        def _check_tags_counts():
            for index, entity in enumerate(entities):
                entity.tags.reload()
                assert entity.tags.subcount == tags_per_entities_count[index]

        collection.action.assign_tags(*entities, tags=new_tags)
        assert_response(appliance, success=False, results_num=tags_count)
        _check_tags_counts()

        collection.action.unassign_tags(*entities, tags=new_tags)
        assert_response(appliance, success=False, results_num=tags_count)
        _check_tags_counts()

    @pytest.mark.tier(3)
    def test_query_by_multiple_tags(self, appliance, tags, services):
        """Tests support for multiple tag specification in query.

        Metadata:
            test_flag: rest

        Polarion:
            assignee: pvala
            casecomponent: Configuration
            caseimportance: high
            initialEstimate: 1/30h
        """
        collection = appliance.rest_api.collections.services
        collection.reload()
        new_tags = [tag._ref_repr() for tag in tags]
        tagged_services = services[1:]

        # assign tags to selected services
        collection.action.assign_tags(*tagged_services, tags=new_tags)
        assert_response(appliance)

        # get only services that has all the tags assigned
        by_tag = ','.join([tag.name.replace('/managed', '') for tag in tags])
        query_results = collection.query_string(by_tag=by_tag)

        assert len(tagged_services) == len(query_results)
        result_ids = {item.id for item in query_results}
        tagged_ids = {item.id for item in tagged_services}
        assert result_ids == tagged_ids
