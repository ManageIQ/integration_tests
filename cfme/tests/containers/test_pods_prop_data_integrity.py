# -*- coding: utf-8 -*-

import pytest
from cfme.fixtures import pytest_selenium as sel
from cfme.containers.pod import Pod
from utils import testgen
from utils.version import current_version
from cfme.web_ui import CheckboxTable


pytestmark = [
    pytest.mark.uncollectif(
        lambda: current_version() < "5.6"),
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.tier(1)]
pytest_generate_tests = testgen.generate(
    testgen.container_providers, scope="function")

# CMP-9934


def test_summary_properties_validation(provider):
    """
          This test verifies that the number of running containers in the status summary table
          is the same number that appears in the Relationships table
    """
    sel.force_navigate('containers_pods')
    list_tbl_pod_new = CheckboxTable(table_locator="//div[@id='list_grid']//table")
    ui_pods = [r.name.text for r in list_tbl_pod_new.rows()]
    ui_pods_revised = filter(
        lambda ch: not ch.startswith('metrics'),
        ui_pods)

    for name in ui_pods_revised:
        obj = Pod(name, provider)
        val_cont_stat_summary = obj.get_detail(
            'Container Statuses Summary', 'Running')
        val_cont_rel_tbl = obj.get_detail('Relationships', 'Containers')
        assert val_cont_rel_tbl == val_cont_stat_summary
