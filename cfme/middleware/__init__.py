from __future__ import unicode_literals
from functools import partial
from random import sample
import os

from cfme.common import Validatable, SummaryMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, Form, fill, flash, FileInput, Input, CFMECheckbox
from cfme.web_ui.form_buttons import FormButton
from utils.browser import ensure_browser_open

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')
pwr_btn = partial(tb.select, 'Power')
download_btn = partial(tb.select, "Download")
deploy_btn = partial(tb.select, 'Deployments')
operations_btn = partial(tb.select, 'Operations')
auth_btn = partial(tb.select, 'Authentication')

LIST_TABLE_LOCATOR = "//div[@id='list_grid']/table"


class MiddlewareBase(Validatable):
    """
    MiddlewareBase class used to define common functions across pages.
    Also used to override existing function when required.
    """

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed('//h1[contains(., "{} (Summary)")]'.format(self.name))


import_form = Form(
    fields=[
        ("file_select", FileInput("upload[file]")),
        ("enable_deployment", CFMECheckbox("enable_deployment_cb")),
        ("runtime_name", Input("runtime_name_input", use_id=True)),
        ('deploy_button', FormButton("Deploy", ng_click="addDeployment()")),
        ('cancel_button', FormButton("Cancel"))
    ]
)


def get_random_list(items, limit):
    """In tests, when we have big list iterating through each element will take lot of time.
    To avoid this, select random list with limited numbers"""
    if len(items) > limit:
        return sample(items, limit)
    else:
        return items


def parse_properties(props):
    """Parses provided properties in string format into dictionary format.
    It splits string into lines and splits each line into key and value."""
    properties = {}
    for line in props.splitlines():
        pair = line.split(': ')
        if len(pair) == 2:
            properties.update({pair[0]: pair[1].replace('\'', '')})
    return properties


def download(extension):
    extensions_mapping = {'txt': 'Text', 'csv': 'CSV'}
    try:
        download_btn("Download as {}".format(extensions_mapping[extension]))
    except:
        raise ValueError("Unknown extention. check the extentions_mapping")


class Container(SummaryMixin):

    def add_deployment(self, filename, runtime_name=None, enable_deploy=True, cancel=False):
        """Clicks to "Add Deployment" button, in opened window fills fields by provided parameters,
        and deploys.

        Args:
            filename: Full path to file to import.
            runtime_name: Runtime name of deployment archive.
            enable_deploy: Whether to enable deployment archive or keep disabled.
            cancel: Whether to click Cancel instead of commit.
        """
        self.load_details()
        deploy_btn("Add Deployment")
        fill(
            import_form,
            {"file_select": filename},
        )
        if runtime_name:
            fill(
                import_form,
                {"runtime_name": runtime_name},
            )
        sel.click(import_form.cancel_button if cancel else import_form.deploy_button)
        flash.assert_success_message('Deployment "{}" has been initiated on this server.'
                    .format(runtime_name if runtime_name else os.path.basename(filename)))


class Deployable(SummaryMixin):

    def undeploy(self):
        """
        Clicks on "Undeploy" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Undeploy", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Undeployment initiated for selected deployment(s)')

    def redeploy(self):
        """
        Clicks on "Redeploy" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Redeploy", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Redeployment initiated for selected deployment(s)')

    def stop(self):
        """
        Clicks on "Stop" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Stop", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Stop initiated for selected deployment(s)')

    def start(self):
        """
        Clicks on "Start" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Start", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Start initiated for selected deployment(s)')
