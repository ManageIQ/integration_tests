# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.provisioning_dialogs import ProvisioningDialogsCollection
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.update import update


@pytest.mark.sauce
@test_requirements.automate
@pytest.mark.tier(3)
def test_provisioning_dialog_crud(appliance):
    """
    Polarion:
        assignee: dmisharo
        casecomponent: automate
        initialEstimate: 1/10h
    """
    # CREATE
    collection = appliance.collections.provisioning_dialogs
    dialog = collection.create(
        name='test-{}'.format(fauxfactory.gen_alphanumeric(length=5)),
        description='test-{}'.format(fauxfactory.gen_alphanumeric(length=5)),
        diag_type=collection.VM_PROVISION)
    assert dialog.exists

    # UPDATE
    with update(dialog):
        dialog.name = fauxfactory.gen_alphanumeric()
        dialog.description = fauxfactory.gen_alphanumeric()
    assert dialog.exists

    with update(dialog):
        dialog.diag_type = collection.HOST_PROVISION
    assert dialog.exists
    # Update with cancel
    dialog.update(updates={'description': 'not saved'}, cancel=True)
    view = navigate_to(dialog, 'Details')
    assert view.entities

    # DELETE
    dialog.delete(cancel=True)
    assert dialog.exists
    dialog.delete()
    assert not dialog.exists


sort_by_params = []
for name in ProvisioningDialogsCollection.ALLOWED_TYPES:
    sort_by_params.append((name, "Name", "ascending"))
    sort_by_params.append((name, "Name", "descending"))
    sort_by_params.append((name, "Description", "ascending"))
    sort_by_params.append((name, "Description", "descending"))


@test_requirements.general_ui
@pytest.mark.tier(3)
@pytest.mark.parametrize(("name", "by", "order"), sort_by_params)
def test_provisioning_dialogs_sorting(appliance, name, by, order):
    """
    Polarion:
        assignee: dmisharo
        casecomponent: automate
        caseimportance: low
        initialEstimate: 1/30h
    """
    view = navigate_to(appliance.collections.provisioning_dialogs, 'All')
    view.sidebar.provisioning_dialogs.tree.click_path("All Dialogs", name)
    view.entities.table.sort_by(by, order)
    # When we can get the same comparing function as the PGSQL DB has, we can check
