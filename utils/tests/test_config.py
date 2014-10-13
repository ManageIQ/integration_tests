import os
from warnings import catch_warnings

import pytest

from utils import conf
from utils._conf import Config, ConfigTree, ConfigNotFound, RecursiveUpdateDict

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


@pytest.fixture
def clear_conf():
    # Ensure the conf is cleared before every test
    conf.clear()
    conf.runtime.clear()
pytestmark = pytest.mark.usefixtures('clear_conf')


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


def test_conf_basics(test_yaml):
    # Dict lookup method works
    assert conf[test_yaml]['test_key'] == 'test_value'
    assert isinstance(conf, Config)
    assert isinstance(conf.runtime, ConfigTree)
    assert isinstance(conf[test_yaml], RecursiveUpdateDict)
    assert isinstance(conf[test_yaml]['nested_test_root'], RecursiveUpdateDict)


def test_conf_yamls_item(test_yaml):
    # delitem doesn't really delete, it only clears in-place
    old_test_yaml = conf[test_yaml]
    del(conf[test_yaml])
    assert conf[test_yaml] is old_test_yaml

    # setitem doesn't really set, it only updates in-place
    conf[test_yaml] = {'foo': 'bar'}
    assert conf[test_yaml] is old_test_yaml


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
    # Make sure the the ConfigNotFound warning is issued correctly
    with catch_warnings(record=True) as warnings:
        conf[random_string]

    # Should only be one warning, the attempt to load a nonexistent conf file should warn,
    # but loading a nonexistent local yaml override should not
    assert len(warnings) == 1
    # The warning we caught should be the correct type, and contain random_string
    assert issubclass(ConfigNotFound, warnings[0].category)
    assert random_string in str(warnings[0].message)


def test_conf_runtime_override(random_string):
    # sanity check: If the random string is in conf.env, INSTANITY.
    assert random_string not in conf.env
    # Add the random string to the runtime dict, as well as a junk value to
    # prove we can add more than one thing via the ConfTree
    conf.runtime['env'][random_string] = True
    conf.runtime['foo'] = 'bar'
    # the override is in place
    assert random_string in conf.env
    conf.clear()
    # the override is still in place
    assert random_string in conf.env
    # deleting works
    del(conf.runtime['env'][random_string])
    assert random_string not in conf.env


def test_conf_runtime_set(random_string):
    # setting runtime directly works, and doesn't change the object that runtime points to
    old_runtime = conf.runtime
    conf.runtime = {'env': {random_string: True}}
    conf.runtime is old_runtime
    assert random_string in conf.env


def test_conf_runtime_update(random_string):
    # In addition to direct nested assignment, dict update should also work
    conf.runtime.update({'env': {random_string: True}})
    assert random_string in conf.env


def test_conf_imported_attr(test_yaml, random_string):
    # "from utils.conf import attr" should be the same object as "conf.attr"
    # mutating the runtime dict shouldn't change that
    imported_test_yaml = getattr(conf, test_yaml)
    conf.runtime[test_yaml]['test_key'] = random_string
    assert imported_test_yaml['test_key'] == random_string
    assert imported_test_yaml is getattr(conf, test_yaml)


def test_conf_override_before_import(test_yaml, random_string):
    # You should be able to create a "fake" config file by preseeding the runtime overrides
    conf.runtime['foo']['test_key'] = random_string
    from utils.conf import foo
    assert foo['test_key'] == random_string
