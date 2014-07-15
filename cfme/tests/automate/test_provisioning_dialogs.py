# -*- coding: utf-8 -*-
import pytest

from cfme.automate import provisioning_dialogs
from utils.randomness import generate_random_string
from utils.update import update


@pytest.yield_fixture(scope="function")
def dialog():
    dlg = provisioning_dialogs.ProvisioningDialog(
        provisioning_dialogs.ProvisioningDialog.VM_PROVISION,
        name=generate_random_string(),
        description=generate_random_string()
    )
    yield dlg
    if dlg.exists:
        dlg.delete()


def test_provisioning_dialog_crud(dialog):
    dialog.create()
    assert dialog.exists
    with update(dialog):
        dialog.name = generate_random_string()
        dialog.description = generate_random_string()
    assert dialog.exists
    dialog.change_type(provisioning_dialogs.ProvisioningDialog.HOST_PROVISION)
    assert dialog.exists
    dialog.delete()
    assert not dialog.exists

sort_by_params = []
for nav_loc, name in provisioning_dialogs.ProvisioningDialog.ALLOWED_TYPES:
    sort_by_params.append((nav_loc, "Name", "ascending"))
    sort_by_params.append((nav_loc, "Name", "descending"))
    sort_by_params.append((nav_loc, "Description", "ascending"))
    sort_by_params.append((nav_loc, "Description", "descending"))


@pytest.mark.bugzilla(1096388)
@pytest.mark.parametrize(("nav_loc", "by", "order"), sort_by_params)
def test_provisioning_dialogs_sorting(nav_loc, by, order):
    pytest.sel.force_navigate("{}_dialogs".format(nav_loc))
    provisioning_dialogs.dialog_table.sort_by(by, order)
    # When we can get the same comparing function as the PGSQL DB has, we can check
