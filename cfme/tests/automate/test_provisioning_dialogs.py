# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate import provisioning_dialogs
from cfme.web_ui import accordion
from utils.update import update
from utils.appliance.endpoints.ui import navigate_to


@pytest.yield_fixture(scope="function")
def dialog():
    dlg = provisioning_dialogs.ProvisioningDialog(
        provisioning_dialogs.ProvisioningDialog.VM_PROVISION,
        name=fauxfactory.gen_alphanumeric(),
        description=fauxfactory.gen_alphanumeric()
    )
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
    dialog.change_type(provisioning_dialogs.ProvisioningDialog.HOST_PROVISION)
    assert dialog.exists
    dialog.delete()
    assert not dialog.exists


sort_by_params = []
for nav_loc, name in provisioning_dialogs.ProvisioningDialog.ALLOWED_TYPES:
    sort_by_params.append((name, "Name", "ascending"))
    sort_by_params.append((name, "Name", "descending"))
    sort_by_params.append((name, "Description", "ascending"))
    sort_by_params.append((name, "Description", "descending"))


@test_requirements.general_ui
@pytest.mark.tier(3)
@pytest.mark.meta(blockers=[1096388])
@pytest.mark.parametrize(("name", "by", "order"), sort_by_params)
def test_provisioning_dialogs_sorting(name, by, order):
    navigate_to(provisioning_dialogs.ProvisioningDialog, 'All')
    accordion.tree("Provisioning Dialogs", "All Dialogs", name)
    provisioning_dialogs.dialog_table.sort_by(by, order)
    # When we can get the same comparing function as the PGSQL DB has, we can check
