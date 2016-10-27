from cfme import web_ui as ui
from cfme.web_ui import form_buttons, CFMECheckbox
from utils.appliance import current_appliance
from utils.appliance.implementations.ui import navigate_to

form = ui.Form(
    fields=[
        ('all_clusters_cb', CFMECheckbox("all_clusters")),
        ('all_datastores_cb', CFMECheckbox("all_storages"))
    ])


def _enable_disable(enable=True):
    navigate_to(current_appliance.server.zone.region, 'CANDUCollection')
    ui.fill(form, {'all_clusters_cb': enable,
                   'all_datastores_cb': enable},
            action=form_buttons.save)


def enable_all():
    """Enable all C&U metric collection for this region"""
    _enable_disable()


def disable_all():
    """Enable all C&U metric collection for this region"""
    _enable_disable(False)
