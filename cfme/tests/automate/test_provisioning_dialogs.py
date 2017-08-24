# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.provisioning_dialogs import ProvisioningDialog
from utils.update import update
from utils.appliance.implementations.ui import navigate_to


@pytest.yield_fixture(scope="function")
def dialog():
    dlg = ProvisioningDialog(
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric(),
        diag_type=ProvisioningDialog.VM_PROVISION)
    yield dlg

    if dlg.exists:
        dlg.delete()


@test_requirements.automate
@pytest.mark.tier(3)
def test_provisioning_dialog_crud(dialog):
    dialog.create()
    assert dialog.exists
    with update(dialog):
        dialog.name = fauxfactory.gen_alphanumeric()
        dialog.description = fauxfactory.gen_alphanumeric()
    assert dialog.exists
    with update(dialog):
        dialog.diag_type = ProvisioningDialog.HOST_PROVISION
    assert dialog.exists
    dialog.delete()
    assert not dialog.exists


sort_by_params = []
for name in ProvisioningDialog.ALLOWED_TYPES:
    sort_by_params.append((name, "Name", "ascending"))
    sort_by_params.append((name, "Name", "descending"))
    sort_by_params.append((name, "Description", "ascending"))
    sort_by_params.append((name, "Description", "descending"))


@test_requirements.general_ui
@pytest.mark.tier(3)
@pytest.mark.parametrize(("name", "by", "order"), sort_by_params)
def test_provisioning_dialogs_sorting(name, by, order):
    view = navigate_to(ProvisioningDialog, 'All')
    view.sidebar.provisioning_dialogs.tree.click_path("All Dialogs", name)
    view.entities.table.sort_by(by, order)
    # When we can get the same comparing function as the PGSQL DB has, we can check
