from functools import partial
from random import sample
import os
import re

from cfme.common import Validatable, SummaryMixin
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, Form, fill, flash, FileInput, Input
from cfme.web_ui import CFMECheckbox, Select
from cfme.web_ui.form_buttons import FormButton
from utils.browser import ensure_browser_open

cfg_btn = partial(tb.select, 'Configuration')
mon_btn = partial(tb.select, 'Monitoring')
pol_btn = partial(tb.select, 'Policy')
pwr_btn = partial(tb.select, 'Power')
download_btn = partial(tb.select, "Download")
download_summary_btn = partial(tb.select, "Download summary in PDF format")
deploy_btn = partial(tb.select, 'Deployments')
operations_btn = partial(tb.select, 'Operations')
auth_btn = partial(tb.select, 'Authentication')
jdbc_btn = partial(tb.select, 'JDBC Drivers')
datasources_btn = partial(tb.select, 'Datasources')

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

    def download_summary(self):
        self.summary.reload()
        download_summary_btn()

import_form = Form(
    fields=[
        ("file_select", FileInput("upload[file]")),
        ("enable_deployment", CFMECheckbox("enable_deployment_cb")),
        ("runtime_name", Input("runtime_name_input", use_id=True)),
        ('deploy_button', FormButton("Deploy", ng_click="addDeployment()")),
        ('cancel_button', FormButton("Cancel"))
    ]
)

jdbc_driver_form = Form(
    fields=[
        ("file_select", FileInput("jdbc_driver[file]")),
        ("jdbc_driver_name", Input("jdbc_driver_name_input")),
        ("jdbc_module_name", Input("jdbc_module_name_input")),
        ("jdbc_driver_class", Input("jdbc_driver_class_input")),
        ("major_version", Input("major_version_input")),
        ("minor_version", Input("minor_version_input")),
        ('deploy_button', FormButton("Deploy", ng_click="addJdbcDriver()")),
        ('cancel_button', FormButton("Cancel"))
    ]
)


datasource_form = Form(
    fields=[
        ("ds_type", Select("//select[@id='chooose_datasource_input']")),
        ("ds_name", Input("ds_name_input")),
        ("jndi_name", Input("jndi_name_input")),
        ("driver_name", Input("jdbc_ds_driver_name_input")),
        ("driver_module_name", Input("jdbc_modoule_name_input")),
        ("driver_class", Input("jdbc_ds_driver_input")),
        ("ds_url", Input("connection_url_input")),
        ("username", Input("user_name_input")),
        ("password", Input("password_input")),
        ("sec_domain", Input("security_domain_input", use_id=True)),
        ('next0_button', FormButton('Next', ng_click="addDatasourceChooseNext()")),
        ('next1_button', FormButton('Next', ng_click="addDatasourceStep1Next()")),
        ('next2_button', FormButton('Next', ng_click="addDatasourceStep2Next()")),
        ('back1_button', FormButton('Back', ng_click="addDatasourceStep1Back()")),
        ('back2_button', FormButton('Back', ng_click="addDatasourceStep2Back()")),
        ('back3_button', FormButton('Back', ng_click="finishAddDatasourceBack()")),
        ('finish_button', FormButton('Finish', ng_click="finishAddDatasource()")),
        ('cancel_button', FormButton('Cancel', ng_click="reset()"))
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
    extensions_mapping = {'txt': 'Text', 'csv': 'CSV', 'pdf': 'PDF'}
    try:
        download_btn("Download as {}".format(extensions_mapping[extension]))
    except:
        raise ValueError("Unknown extention. check the extentions_mapping")


def get_server_name(path):
    if len(path.resource_id) > 3:
        # this is the domain mode case, take the server value
        return re.sub(r'.*server%3D', '', path.resource_id[2])
    else:
        # for standalone servers
        return re.sub(r'~~$', '', path.resource_id[0])


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
        if not enable_deploy:
            fill(
                import_form,
                {"enable_deployment": enable_deploy}
            )
        sel.click(import_form.cancel_button if cancel else import_form.deploy_button)
        flash.assert_success_message('Deployment "{}" has been initiated on this server.'
                    .format(runtime_name if runtime_name else os.path.basename(filename)))

    def add_jdbc_driver(self, filename, driver_name, module_name, driver_class,
                        major_version=None, minor_version=None, cancel=False):
        """Clicks to "Add JDBC Driver" button, in opened window fills fields by provided parameters,
        and deploys.

        Args:
            filename: Full path to JDBC Driver to import.
            driver_name: Name of newly created JDBC Driver.
            module_name: Name on Module to register on server side.
            driver_class: JDBC Driver Class.
            major_version: Major version of JDBC driver, optional.
            minor_version: Minor version of JDBC driver, optional.
            cancel: Whether to click Cancel instead of commit.
        """
        self.load_details(refresh=True)
        jdbc_btn("Add JDBC Driver")
        fill(jdbc_driver_form,
            {
                "file_select": filename,
                "jdbc_driver_name": driver_name,
                "jdbc_module_name": module_name,
                "jdbc_driver_class": driver_class,
                "major_version": major_version,
                "minor_version": minor_version
            })
        sel.click(jdbc_driver_form.cancel_button if cancel else jdbc_driver_form.deploy_button)
        flash.assert_success_message('JDBC Driver "{}" has been installed on this server.'
                    .format(driver_name))

    def add_datasource(self, ds_type, ds_name, jndi_name, driver_name,
               driver_module_name, driver_class, ds_url,
               username, password=None, sec_domain=None, cancel=False):
        """Clicks to "Add Datasource" button,
        in opened window fills fields by provided parameter by clicking 'Next',
        and submits the form by clicking 'Finish'.

        Args:
            ds_type: Type of database.
            ds_name: Name of newly created Datasource.
            jndi_name: JNDI Name of Datasource.
            driver_name: JDBC Driver name in Datasource.
            driver_module_name: Module name of JDBC Driver used in datasource.
            driver_class: JDBC Driver Class.
            ds_url: Database connection URL in jdbc format.
            username: Database username.
            password: Databasae password, optional.
            sec_domain: Security Domain, optional.
            cancel: Whether to click Cancel instead of commit.
        """
        self.load_details(refresh=True)
        datasources_btn("Add Datasource", invokes_alert=True)
        fill(datasource_form,
            {
                "ds_type": ds_type
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.next0_button)
        fill(datasource_form,
            {
                "ds_name": ds_name,
                "jndi_name": jndi_name
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.next1_button)
        fill(datasource_form,
            {
                "driver_name": driver_name,
                "driver_module_name": driver_module_name,
                "driver_class": driver_class
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.next2_button)
        fill(datasource_form,
            {
                "ds_url": ds_url,
                "username": username,
                "password": password,
                "sec_domain": sec_domain
            })
        sel.click(datasource_form.cancel_button if cancel else datasource_form.finish_button)
        flash.assert_no_errors()


class Deployable(SummaryMixin):

    def undeploy(self):
        """
        Clicks on "Undeploy" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Undeploy", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Undeployment initiated for selected deployment(s)')

    def restart(self):
        """
        Clicks on "Restart" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Restart", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Restart initiated for selected deployment(s)')

    def disable(self):
        """
        Clicks on "Disable" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Disable", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Disable initiated for selected deployment(s)')

    def enable(self):
        """
        Clicks on "Enable" menu item and verifies message shown
        """
        self.load_details()
        operations_btn("Enable", invokes_alert=True)
        sel.handle_alert()
        flash.assert_success_message('Enable initiated for selected deployment(s)')
