# -*- coding: utf-8 -*-

import pytest

from cfme.control import import_export
from utils.path import data_path
from cfme.web_ui import flash
from cfme.exceptions import CFMEException, FlashMessageException


@pytest.fixture(scope="module")
def import_policy_file(request):
    return data_path.join("ui/control/policies.yaml").realpath().strpath


@pytest.fixture(scope="module")
def import_invalid_yaml_file(request):
    return data_path.join("ui/control/invalid.yaml").realpath().strpath


@pytest.mark.meta(blockers=[1106456, 1198111], automates=[1198111])
@pytest.sel.go_to('control_import_export')
def test_import_policies(import_policy_file):
    import_export.import_file(import_policy_file)
    flash.assert_no_errors()


@pytest.sel.go_to('control_import_export')
def test_control_import_invalid_yaml_file(import_invalid_yaml_file):
    try:
        import_export.import_file(import_invalid_yaml_file)
    except FlashMessageException:
        pass
    else:
        raise CFMEException
