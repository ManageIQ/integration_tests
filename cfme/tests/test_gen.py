import pytest
from utils import testgen

pytest_generate_tests = testgen.generate(testgen.infra_providers)


@pytest.fixture(scope="module")
def fixture():
    pass


def test_gen(provider_crud, setup_provie):
    print 'provider setup', setup_provie
