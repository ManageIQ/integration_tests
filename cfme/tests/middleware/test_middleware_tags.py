import pytest
from cfme.configure.configuration import Category, Tag
from cfme.middleware.datasource import MiddlewareDatasource
from cfme.middleware.server import MiddlewareServer
from cfme.middleware.provider.hawkular import HawkularProvider
from cfme.middleware.deployment import MiddlewareDeployment
from cfme.middleware.domain import MiddlewareDomain
from cfme.middleware.server_group import MiddlewareServerGroup
from cfme.middleware.messaging import MiddlewareMessaging
from random_methods import get_random_object
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


@pytest.mark.parametrize("objecttype", [MiddlewareDatasource, MiddlewareDeployment,
                                        HawkularProvider, MiddlewareServer,
                                        MiddlewareDomain, MiddlewareMessaging,
                                        MiddlewareServerGroup])
def test_object_tags(provider, objecttype):
    """Tests tags in all taggable pages

    Steps:
        * Select a taggable object of provided objecttype randomly from database
        * Run `_validate_tags` with `tags` input
    """
    taggable = get_random_object(provider, objecttype)
    validate_tags(taggable=taggable, tags=tags)


def validate_tags(taggable, tags):
    """Remove all tags and add `tags` from user input, validates added tags"""
    tags_db = taggable.get_tags(method='db')
    if len(tags_db) > 0:
        taggable.remove_tags(tags=tags_db)
        tags_db = taggable.get_tags(method='db')
    assert len(tags_db) == 0, "Some of tags still available in database!"
    taggable.add_tags(tags)
    taggable.validate_tags(reference_tags=tags)
