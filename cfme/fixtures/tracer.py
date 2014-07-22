import os.path
import function_trace
# disable traceback of the tracer functions
function_trace.__tracebackhide__ = True

# import everything we want to trace

import cfme.automate.explorer
import cfme.automate.service_dialogs
import cfme.cloud.instance
import cfme.cloud.provider
import cfme.cloud.provisioning
import cfme.cloud.security_group
import cfme.configure.configuration
import cfme.configure.red_hat_updates
import cfme.configure.tasks
import cfme.configure.access_control
import cfme.control.explorer
import cfme.control.import_export
import cfme.control.snmp_form
import cfme.fixtures.pytest_selenium
import cfme.infrastructure.datastore
import cfme.infrastructure.host
import cfme.infrastructure.provider
import cfme.infrastructure.provisioning
import cfme.infrastructure.pxe
import cfme.infrastructure.virtual_machines
import cfme.intelligence.chargeback
import cfme.intelligence.reports.dashboards
import cfme.intelligence.reports.import_export
import cfme.intelligence.reports.reports
import cfme.intelligence.reports.saved
import cfme.intelligence.reports.schedules
import cfme.intelligence.reports.ui_elements
import cfme.intelligence.reports.widgets
import cfme.login
import cfme.services.requests
import cfme.services.catalogs.catalog_item
import cfme.services.catalogs.catalog
import cfme.services.catalogs.cloud_catalog_item
import cfme.services.catalogs.service_catalogs
import cfme.web_ui
import cfme.web_ui.accordion
import cfme.web_ui.flash
import cfme.web_ui.cfme_exception
import cfme.web_ui.expression_editor
import cfme.web_ui.form_buttons
import cfme.web_ui.listaccordion
import cfme.web_ui.menu
import cfme.web_ui.multibox
import cfme.web_ui.paginator
import cfme.web_ui.search
import cfme.web_ui.tabstrip
import cfme.web_ui.toolbar
from fixtures.artifactor_plugin import art_client


default_to_trace = function_trace.mapcat(
    function_trace.all,
    [
        cfme.automate.explorer,
        cfme.automate.service_dialogs,
        cfme.cloud.instance,
        cfme.cloud.provider,
        cfme.cloud.provisioning,
        cfme.cloud.security_group,
        cfme.configure.configuration,
        cfme.configure.red_hat_updates,
        cfme.configure.tasks,
        cfme.configure.access_control,
        cfme.control.explorer,
        cfme.control.import_export,
        cfme.control.snmp_form,
        cfme.fixtures.pytest_selenium,
        cfme.infrastructure.datastore,
        cfme.infrastructure.host,
        cfme.infrastructure.provider,
        cfme.infrastructure.provisioning,
        cfme.infrastructure.pxe,
        cfme.infrastructure.virtual_machines,
        cfme.intelligence.chargeback,
        cfme.intelligence.reports.dashboards,
        cfme.intelligence.reports.import_export,
        cfme.intelligence.reports.reports,
        cfme.intelligence.reports.saved,
        cfme.intelligence.reports.schedules,
        cfme.intelligence.reports.ui_elements,
        cfme.intelligence.reports.widgets,
        cfme.login,
        cfme.services.requests,
        cfme.services.catalogs.catalog_item,
        cfme.services.catalogs.catalog,
        cfme.services.catalogs.catalog.Catalog,
        cfme.services.catalogs.service_catalogs,
        cfme.web_ui,
        cfme.web_ui.accordion,
        cfme.web_ui.cfme_exception,
        cfme.web_ui.expression_editor,
        cfme.web_ui.flash,
        cfme.web_ui.form_buttons,
        cfme.web_ui.listaccordion,
        cfme.web_ui.menu,
        cfme.web_ui.multibox,
        cfme.web_ui.paginator,
        cfme.web_ui.search,
        cfme.web_ui.tabstrip,
        cfme.web_ui.toolbar
    ])
# 0 = do not trace into
default_depths = {cfme.fixtures.pytest_selenium.wait_until: 0,
                  cfme.fixtures.pytest_selenium.wait_for_ajax: 0,
                  cfme.fixtures.pytest_selenium.elements: 0,
                  cfme.fixtures.pytest_selenium.element: 0,
                  cfme.fixtures.pytest_selenium.browser: 0,
                  cfme.fixtures.pytest_selenium.move_to_element: 0,
                  cfme.fixtures.pytest_selenium.wait_for_element: 0,
                  cfme.fixtures.pytest_selenium.click: 1,
                  cfme.fixtures.pytest_selenium.set_text: 1,
                  cfme.fixtures.pytest_selenium.detect_observed_field: 0,
                  cfme.fixtures.pytest_selenium.select: 1,
                  cfme.fixtures.pytest_selenium.check: 1,
                  cfme.web_ui.toolbar.is_greyed: 1,
                  cfme.web_ui.flash.message: 1,
                  cfme.web_ui.fill_tag: 0
                  }

to_trace = default_to_trace
depths = default_depths


def pytest_addoption(parser):
    parser.addoption("--no-tracer", dest="tracer", action="store_false", default=True,
                     help="Disable the function tracer")


def pytest_runtest_call(__multicall__, item):
    """hook to run each test with traced function calls"""
    if item.config.getvalue('tracer'):
        out = art_client.fire_hook('filedump', grab_result=True,
                                   test_name=item.name, test_location=item.parent.name,
                                   filename="function_trace.txt", contents="",
                                   fd_ident="func_trace")
        with function_trace.trace_on(
                tracer=function_trace.PerThreadFileTracer(
                    to_trace,
                    depths=depths,
                    filename=os.path.join(out['artifact_path'], 'filedump-function_trace.txt'))):
            __multicall__.execute()


# fix the representation of various classes to not suck

# setattr(webelement.WebElement, '__repr__', pretty.pr_obj(['tag_name', 'id', 'text']))
# setattr(Exception, '__repr__', pretty.pr_obj(['message']))
