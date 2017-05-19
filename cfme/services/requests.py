# -*- coding: utf-8 -*-
from contextlib import contextmanager
from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Table, Checkbox
from widgetastic_manageiq import BreadCrumb, SummaryFormItem
from widgetastic_patternfly import Button, View, Input, Tab, BootstrapTreeview

from cfme.base.login import BaseLoggedInPage
from cfme.exceptions import RequestException
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, PagedTable, flash, paginator, toolbar, match_location)
from utils.log import logger
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


request_table = PagedTable(table_locator='//*[@id="list_grid"]/table')

fields = Region(
    locators=dict(
        reason=Input("reason"),
        request_list=request_table
    )
)

match_page = partial(match_location, controller='miq_request', title='Requests')


def find_request(cells, partial_check=False):
    """Finds the request and returns the row element

    Args:
        cells: Search data for the requests table.
        partial_check: If to use the ``in`` operator rather than ``==`` in find_rows_by_cells().
    Returns: row
    """
    navigate_to(Request, 'All')
    for page in paginator.pages():
        results = fields.request_list.find_rows_by_cells(cells, partial_check)
        if len(results) == 0:
            # row not on this page, assume it has yet to appear
            # it might be nice to add an option to fail at this point
            continue
        elif len(results) > 1:
            raise RequestException(
                'Multiple requests with matching content found - be more specific!'
            )
        else:
            # found the row!
            row = results[0]
            logger.debug(' Request Message: %s', row.last_message.text)
            return row
    else:
        raise Exception("The requst specified by {} not found!".format(str(cells)))
        return False


class Request(Navigatable):
    def __init__(self, row_description=None, cells=None, partial_check=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.row_description = row_description
        self.cells = {'Description': self.row_description} if not cells else cells
        self.partial_check = partial_check
        self.REQUEST_FINISHED_STATES = {'Migrated', 'Finished'}
        self.row = find_request(self.cells, self.partial_check)
        self.request_id = self.row.request_id.text
        self.description = self.row.description.text

    @property
    def if_exists(self):
        return True if find_request(cells=self.cells, partial_check=self.partial_check) else False

    def load_details(self):
        return navigate_to(self, 'Details')

    def reload(self):
        toolbar.refresh()

    def update_row(self):
        """Updates Request object details - last message, status etc
        """
        self.row = find_request(self.cells, self.partial_check)

    def approve_request(self, reason, cancel=False):
        """Approves request with specified reason

        Args:
            reason: Reason for approving the request.
            cancel: Whether to cancel the approval.

        """
        view = self.load_details()
        view.approve(reason, cancel)

    def deny_request(self, reason, cancel=False):
        """Open the specified request and deny it.

        Args:
            reason: Reason for denying the request.
            cancel: Whether to cancel the denial.

        """
        view = self.load_details()
        view.deny(reason, cancel)

    def delete_request(self, cancel=False):
        """Open the specified request and delete it.

        Args:
            cancel: Whether to cancel the deletion.
        """
        view = self.load_details()
        view.delete(cancel)

    def is_finished(self):
        """Helper function checks if a request is completed
        """
        self.update_row()
        self.row = find_request(self.cells, self.partial_check)
        if self.row.request_state.text in self.REQUEST_FINISHED_STATES:
            return True
        else:
            return False

    def if_succeeded(self):
        self.row = find_request(self.cells, self.partial_check)
        if self.is_finished() and self.row.status.text == 'Ok':
            return True
        else:
            return False

    def debug_request(self):
        self.row = find_request(self.cells, self.partial_check)
        logger.debug('Last Message of request: {}', self.row.last_message.text)

    @contextmanager
    def copy_request(self):
        """Context manager that opens the request for editing and saves or cancels depending on success.
        """
        view = self.load_details()
        view.toolbar.copy.click()
        try:
            yield
        except Exception:
            view.cancel.click()
            raise
        else:
            from cfme.provisioning import provisioning_form
            btn = provisioning_form.submit_copy_button
            sel.wait_for_element(btn)
            sel.click(btn)
            flash.assert_no_errors()

    @contextmanager
    def edit_request(self):
        """Context manager that opens the request for editing and saves or cancels depending on success.
        """
        view = self.load_details()
        view.toolbar.edit.click()
        from cfme.provisioning import provisioning_form
        try:
            yield provisioning_form
        except Exception as e:
            logger.exception(e)
            view.cancel.click()
            raise
        else:
            sel.click(provisioning_form.submit_copy_button)
            flash.assert_no_errors()


class RequestView(BaseLoggedInPage):
    title = Text('#explorer_title_text')
    table = Table(locator='//*[@id="list_grid"]/table')

    @property
    def in_requests(self):
        return (self.logged_in_as_current_user and
                self.navigation.currently_selected == ['Services', 'Requests'])

    def open_request(self, cells):
        row = self.table.row(description=cells)
        row.description.click()

    @property
    def is_displayed(self):
        return self.in_requests


class RequestDetailsToolBar(RequestView):
    copy = Button(title='Copy original Request')
    edit = Button(title='Edit the original Request')
    delete = Button(title='Delete this Request')
    reload = Button(title='Reload the current display')
    approve = Button(title='Approve this Request')
    deny = Button(title='Deny this Request')


class RequestDetailsView(RequestView):
    @View.nested
    class details(View):  # noqa
        request_id = SummaryFormItem('Request Details', 'Request ID')
        status = SummaryFormItem('Request Details', 'Status')
        request_state = SummaryFormItem('Request Details', 'Request State')
        requester = SummaryFormItem('Request Details', 'Requester')
        request_type = SummaryFormItem('Request Details', 'Request Type')
        description = SummaryFormItem('Request Details', 'Description')
        last_message = SummaryFormItem('Request Details', 'Last Message')
        created_on = SummaryFormItem('Request Details', 'Created On')
        last_update = SummaryFormItem('Request Details', 'Last Update')
        completed = SummaryFormItem('Request Details', 'Completed')
        approval_state = SummaryFormItem('Request Details', 'Approval State')
        approved_by = SummaryFormItem('Request Details', 'Approved/Denied by')
        approved_on = SummaryFormItem('Request Details', 'Approved/Denied on')
        reason = SummaryFormItem('Request Details', 'Reason')
        provisioned_vms = SummaryFormItem('Request Details', 'Provisioned VMs')

    @View.nested
    class request(Tab):  # noqa
        TAB_NAME = 'Request'
        email = SummaryFormItem('Request Information', 'E-Mail')
        first_name = SummaryFormItem('Request Information', 'First Name')
        last_name = SummaryFormItem('Request Information', 'Last Name')
        notes = SummaryFormItem('Request Information', 'Notes')
        manager_name = SummaryFormItem('Manager', 'Name')

    @View.nested
    class purpose(Tab):  # noqa
        TAB_NAME = 'Purpose'
        apply_tags = BootstrapTreeview('all_tags_treebox')

    @View.nested
    class catalog(Tab):  # noqa
        TAB_NAME = 'Catalog'
        filter = SummaryFormItem('Select', 'Filter')
        name = SummaryFormItem('Select', 'Name')
        provision_type = SummaryFormItem('Select', 'Provision Type')
        linked_clone = Checkbox(id='service__linked_clone')
        vm_count = SummaryFormItem('Number of VMs', 'Count')
        instance_count = SummaryFormItem('Number of Instances', 'Count')
        vm_name = SummaryFormItem('Naming', 'VM Name')
        instance_name = SummaryFormItem('Naming', 'Instance Name')
        vm_description = SummaryFormItem('Naming', 'VM Description')

    @View.nested
    class environment(Tab):  # noqa
        TAB_NAME = 'Environment'

        automatic_placement = Checkbox(name='environment__placement_auto')
        # Azure
        virtual_private_cloud = SummaryFormItem('Placement - Options', 'Virtual Private Cloud')
        cloud_subnet = SummaryFormItem('Placement - Options', 'Cloud Subnet')
        security_groups = SummaryFormItem('Placement - Options', 'Security Groups')
        resource_groups = SummaryFormItem('Placement - Options', 'Resource Groups')
        public_ip_address = SummaryFormItem('Placement - Options', 'Public IP Address ')
        # GCE
        availability_zone = SummaryFormItem('Placement - Options', 'Availability Zones')
        cloud_network = SummaryFormItem('Placement - Options', 'Cloud Network')
        # Infra
        datacenter = SummaryFormItem('Datacenter', 'Name')
        cluster = SummaryFormItem('Cluster', 'Name')
        resource_pool = SummaryFormItem('Resource Pool', 'Name')
        folder = SummaryFormItem('Folder', 'Name')
        host_filter = SummaryFormItem('Host', 'Filter')
        host_name = SummaryFormItem('Host', 'Name')
        datastore_storage_profile = SummaryFormItem('Datastore', 'Storage Profile')
        datastore_filter = SummaryFormItem('Datastore', 'Filter')
        datastore_name = SummaryFormItem('Datastore', 'Name')

    @View.nested
    class hardware(Tab):  # noqa
        num_cpus = SummaryFormItem('Hardware', 'Number of CPUS')
        memory = SummaryFormItem('Hardware', 'Startup Memory (MB)')
        dynamic_memory = SummaryFormItem('Hardware', 'Dynamic Memory')
        vm_limit_cpu = SummaryFormItem('VM Limits', 'CPU (%)')
        vm_reserve_cpu = SummaryFormItem('VM Reservations', 'CPU (%)')

    @View.nested
    class network(Tab):  # noqa
        vlan = SummaryFormItem('Network Adapter Information', 'vLan')

    @View.nested
    class properties(Tab):  # noqa
        instance_type = SummaryFormItem('Properties', 'Instance Type')
        boot_disk_size = SummaryFormItem('Properties', 'Boot Disk Size ')
        is_preemtible = Checkbox(name='hardware__is_preemptible')

    @View.nested
    class customize(Tab):  # noqa
        username = SummaryFormItem('Credentials', 'Username')
        ip_mode = SummaryFormItem('IP Address Information', 'Address Mode')
        hostname = SummaryFormItem('IP Address Information', 'Address Mode')
        subnet_mask = SummaryFormItem('IP Address Information', 'Subnet Mask')
        gateway = SummaryFormItem('IP Address Information', 'Gateway')
        dns_server_list = SummaryFormItem('DNS', 'DNS Server list')
        dns_suffix_list = SummaryFormItem('DNS', 'DNS Suffix list')
        subnet_mask = SummaryFormItem('IP Address Information', 'Subnet Mask')
        customize_template = SummaryFormItem('Customize Template', 'Script Name')

    @View.nested
    class schedule(Tab):  # noqa
        when_provision = SummaryFormItem('Schedule Info', 'When to Provision')
        stateless = Checkbox(name='shedule__stateless')
        power_on = SummaryFormItem('Lifespan', 'Power on virtual machines after creation')
        retirement = SummaryFormItem('Lifespan', 'Time until Retirement')
        retirement_warning = SummaryFormItem('Lifespan', 'Retirement Warning')

    breadcrumb = BreadCrumb()
    toolbar = RequestDetailsToolBar()
    reason = Input(name='reason')
    submit = Button(title='Submit')
    cancel = Button(title="Cancel this provisioning request")

    def approve(self, reason_text, cancel=False):
        """Approve currently opened request

        Args:
            reason_text: Reason for approving the request.
            cancel: Cancel Approval and move to all request list
        """
        self.toolbar.approve.click()
        self.reason.fill(reason_text)
        if not cancel:
            self.submit.click()
        else:
            self.breadcrumb.click_location(self.breadcrumb.locations[0])
        flash.assert_no_errors()

    def deny(self, reason_text, cancel=False):
        """Deny currently opened request

        Args:
            reason_text: Reason for denying the request.
            cancel:  Cancel Denial and move to all request list
        """
        self.toolbar.deny.click()
        self.reason.fill(reason_text)
        if not cancel:
            self.submit.click()
        else:
            self.breadcrumb.click_location(self.breadcrumb.locations[0])
        flash.assert_no_errors()

    def delete(self, cancel=False):
        """Delete currently opened request

        Args:
            cancel: Whether to cancel the deletion.
        """
        self.toolbar.delete.click()
        sel.handle_alert(cancel)
        sel.wait_for_ajax()
        flash.assert_no_errors()


@navigator.register(Request, 'All')
class RequestAll(CFMENavigateStep):
    VIEW = RequestView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def am_i_here(self, *args, **kwargs):
        return match_page(summary='Requests')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Requests')


@navigator.register(Request, 'Details')
class RequestDetails(CFMENavigateStep):
    VIEW = RequestDetailsView
    prerequisite = NavigateToSibling('All')

    def am_i_here(self, *args, **kwargs):
        return match_page(summary=self.obj.description)

    def step(self, *args, **kwargs):
        try:
            return sel.click(request_table.find_row_by_cells(self.obj.cells,
                                                             self.obj.partial_check))
        except (NameError, TypeError):
            logger.warning('Exception caught, could not match Request')
