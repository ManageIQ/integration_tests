from __future__ import unicode_literals
import pytest
from cfme.configure.configuration import Category, Tag
from cfme.middleware import get_random_list
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.deployment import MiddlewareDeployment
from utils import testgen
from utils.version import current_version

pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.uncollectif(lambda: current_version() < '5.7'),
]
pytest_generate_tests = testgen.generate(testgen.provider_by_type, ["hawkular"], scope="function")

tags = [
    Tag(category=Category(display_name='Environment', single_value=True), display_name='Test'),
    Tag(category=Category(display_name='Location', single_value=True), display_name='New York'),
    Tag(category=Category(display_name='Workload', single_value=False),
        display_name='Application Servers'),
]


def test_provider_tags(provider):
    """Tests tags in provider page

    Steps:
        * Run `_validate_tags` with `tags` input
    """
    validate_tags(taggable=provider, tags=tags)


def test_deployment_tags(provider):
    """Tests tags in deployment page

    Steps:
        * Select a deployment randomly from database
        * Run `_validate_tags` with `tags` input
    """
    deps_db = MiddlewareDeployment.deployments_in_db(provider=provider)
    assert len(deps_db) > 0, "There is no deployment(s) available in UI"
    deployment = get_random_list(deps_db, 1)[0]
    validate_tags(taggable=deployment, tags=tags)


def test_datasource_tags(provider):
    """Tests tags in datasources page

    Steps:
        * Select a datasource randomly from database
        * Run `_validate_tags` with `tags` input
    """
    ds_db = MiddlewareDatasource.datasources_in_db(provider=provider)
    assert len(ds_db) > 0, "There is no datasource(s) available in UI"
    datasource = get_random_list(ds_db, 1)[0]
    validate_tags(taggable=datasource, tags=tags)


def test_server_tags(provider):
    """Tests tags in server page

    Steps:
        * Select a server randomly from database
        * Run `_validate_tags` with `tags` input
    """
    servers_db = MiddlewareServer.servers_in_db(provider=provider)
    assert len(servers_db) > 0, "There is no server(s) available in DB"
    server = get_random_list(servers_db, 1)[0]
    validate_tags(taggable=server, tags=tags)


def validate_tags(taggable, tags):
    """Remove all tags and add `tags` from user input, validates added tags"""
    tags_db = taggable.get_tags(method='db')
    if len(tags_db) > 0:
        taggable.remove_tags(tags=tags_db)
        tags_db = taggable.get_tags(method='db')
    assert len(tags_db) == 0, "Some of tags still available in database!"
    taggable.add_tags(tags)
    taggable.validate_tags(reference_tags=tags)
