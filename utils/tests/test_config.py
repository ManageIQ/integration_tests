import os

import pytest

from utils import conf
from utils._conf import Config, RecursiveUpdateDict

test_yaml_contents = '''
test_key: test_value
nested_test_root:
    nested_test_key_1: nested_test_value_1
    nested_test_key_2: nested_test_value_2
'''

local_test_yaml_contents = '''
test_key: test_overridden_value
nested_test_root:
    nested_test_key_1: overridden_nested_test_value
'''


@pytest.fixture(scope='function')
def test_yaml(request, random_string):
    test_yaml = create_test_yaml(request, test_yaml_contents, random_string)
    filename, ext = os.path.splitext(os.path.basename(test_yaml.name))
    return filename


# This is broken out into a non-fixture func
# to facilitate making local yamls overrides
def create_test_yaml(request, contents, filename, local=False):
    if local:
        suffix = '.local.yaml'
    else:
        suffix = '.yaml'
    filename += suffix

    confdir = request.session.fspath.join('conf')
    full_path = str(confdir.join(filename))

    test_yaml = open(full_path, 'w')
    test_yaml.write(contents)
    test_yaml.flush()
    test_yaml.seek(0)

    request.addfinalizer(lambda: os.remove(full_path))
    request.addfinalizer(lambda: conf.clear())

    return test_yaml


def test_conf_yamls_dict(test_yaml):
    # Dict lookup method works
    assert conf[test_yaml]['test_key'] == 'test_value'
    assert isinstance(conf, Config)
    assert isinstance(conf[test_yaml], RecursiveUpdateDict)
    assert isinstance(conf[test_yaml]['nested_test_root'], RecursiveUpdateDict)


def test_conf_yamls_attr(test_yaml):
    # Attribute lookup method works
    assert getattr(conf, test_yaml)['test_key'] == 'test_value'


def test_conf_yamls_override(request, test_yaml):
    # Make a .local.yaml file with the same root name as test_yaml,
    with create_test_yaml(request, local_test_yaml_contents, test_yaml, local=True):
        # Check that the simple local override works.
        assert conf[test_yaml]['test_key'] == 'test_overridden_value'

        # Check that the local override of specific nested keys works.
        nested_root = conf[test_yaml]['nested_test_root']
        assert nested_root['nested_test_key_1'] == 'overridden_nested_test_value'
        assert nested_root['nested_test_key_2'] == 'nested_test_value_2'


def test_conf_yamls_import(test_yaml):
    # Emulate from utils.conf import $test_yaml
    mod = __import__('utils.conf', globals(), locals(), [test_yaml])
    assert getattr(mod, test_yaml) == conf[test_yaml]


def test_conf_yamls_not_found(random_string):
    # Make sure the the raising of ConfigNotFoundException
    # is caught as conf.NotFoundException
    try:
        conf[random_string]
    except conf.NotFoundException:
        # test passes, return out
        return

    pytest.fail('conf.NotFoundException not raised for nonexistent yaml')
