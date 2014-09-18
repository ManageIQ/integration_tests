from cfme import web_ui as ui
from cfme.web_ui import form_buttons
import cfme.fixtures.pytest_selenium as sel

form = ui.Form(
    fields=[
        ('all_clusters_cb', "//input[@type='checkbox' and @id='all_clusters']"),
        ('all_datastores_cb',
         "//input[@type='checkbox' and @name='all_storages' and @data-miq_observe_checkbox]")
    ])


def _enable_disable(enable=True):
    sel.force_navigate("cfg_settings_region_cu_collection")
    ui.fill(form, {'all_clusters_cb': enable,
                   'all_datastores_cb': enable},
            action=form_buttons.save)


def enable_all():
    """Enable all C&U metric collection for this region"""
    _enable_disable()


def disable_all():
    """Enable all C&U metric collection for this region"""
    _enable_disable(False)
