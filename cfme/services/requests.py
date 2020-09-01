from copy import copy

import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from varmeth import variable
from widgetastic.widget import Checkbox
from widgetastic.widget import Table
from widgetastic.widget import Text
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import BootstrapTreeview
from widgetastic_patternfly import BreadCrumb
from widgetastic_patternfly import Input

from cfme.common import BaseLoggedInPage
from cfme.common.vm_views import BasicProvisionFormView
from cfme.common.vm_views import ProvisionView
from cfme.exceptions import displayed_not_implemented
from cfme.exceptions import ItemNotFound
from cfme.exceptions import RequestException
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from widgetastic_manageiq import Button
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import SummaryForm
from widgetastic_manageiq import SummaryFormItem
from widgetastic_manageiq import WaitTab


@attr.s
class Request(BaseEntity):
    """
    Class describes request row from Services - Requests page
    """

    REQUEST_FINISHED_STATES = {'Migrated', 'Finished'}

    description = attr.ib(default=None)
    message = attr.ib(default=None)
    partial_check = attr.ib(default=False)
    cells = attr.ib(default=None)
    row = attr.ib(default=None, init=False)

    def __attrs_post_init__(self):
        self.cells = self.cells or {'Description': self.description}

    # TODO Replace varmeth with Sentaku one day
    @variable(alias='rest')
    def wait_for_request(self, num_sec=1800, delay=20):
        def _finished():
            self.rest.reload()
            return (self.rest.request_state.title() in self.REQUEST_FINISHED_STATES and
                    'Retry' not in self.rest.message)

        def last_message():
            logger.info(f"Last Request message: '{self.rest.message}'")

        wait_for(_finished, num_sec=num_sec, delay=delay, fail_func=last_message,
                 message="Request finished")

    @wait_for_request.variant('ui')
    def wait_for_request_ui(self, num_sec=1200, delay=10):
        def _finished():
            self.update(method='ui')
            return (self.row.request_state.text in self.REQUEST_FINISHED_STATES and
                    'Retry' not in self.row.last_message.text)

        def last_message():
            logger.info(f"Last Request message in UI: '{self.row.last_message}'")

        wait_for(_finished, num_sec=num_sec, delay=delay, fail_func=last_message,
                 message="Request finished")

    @property
    def rest(self):
        if self.partial_check:
            matching_requests = self.appliance.rest_api.collections.requests.find_by(
                description=f'%{self.cells["Description"]}%')
        else:
            matching_requests = self.appliance.rest_api.collections.requests.find_by(
                description=self.cells['Description'])

        if len(matching_requests) > 1:
            # TODO: This forces anything using requests to handle this exception
            # The class needs support for identifying a request by its ID
            # This ID might not be available on instantiation, but needs to be set somehow
            # Ideally before MIQ receives multiple orders for the same service, which have same desc
            raise RequestException(
                f'Multiple requests with matching "{self.description}" found - be more specific!'
            )
        elif len(matching_requests) == 0:
            raise ItemNotFound(
                f'Nothing matching "{self.cells["Description"]}" with '
                f'partial_check={self.partial_check} was found'
            )
        else:
            return matching_requests[0]

    def get_request_row_from_ui(self):
        """Opens CFME UI and return table_row object"""
        view = navigate_to(self.parent, 'All')
        self.row = view.find_request(self.cells, partial_check=self.partial_check)
        return self.row

    def get_request_id(self):
        return self.rest.request_id

    @variable(alias='rest')
    def exists(self):
        """If our Request exists in CFME"""
        try:
            return self.rest.exists
        except ItemNotFound:
            return False

    @property
    def status(self):
        self.update()
        return self.rest.status

    @property
    def request_state(self):
        self.update()
        return self.rest.request_state

    @exists.variant('ui')
    def exists_ui(self):
        """
        Checks if Request if shown in CFME UI.
        Request might be removed from CFME UI but present in DB

        """
        view = navigate_to(self.parent, 'All')
        return bool(view.find_request(self.cells, self.partial_check))

    @variable(alias='rest')
    def update(self):
        """Updates Request object details - last message, status etc
        """
        self.rest.reload()
        self.description = self.rest.description
        self.message = self.rest.message
        self.cells = {'Description': self.description}

    @update.variant('ui')
    def update_ui(self):
        view = navigate_to(self.parent, 'All')
        view.toolbar.reload.click()
        self.row = view.find_request(cells=self.cells, partial_check=self.partial_check)

    @variable(alias='rest')
    def approve_request(self, reason):
        """Approves request with specified reason
        Args:
            reason: Reason for approving the request.
            cancel: Whether to cancel the approval.
        """
        self.rest.action.approve(reason=reason)

    @approve_request.variant('ui')
    def approve_request_ui(self, reason, cancel=False):
        view = navigate_to(self, 'Approve')
        view.reason.fill(reason)
        if not cancel:
            view.submit.click()
        else:
            view.breadcrumb.click_location(view.breadcrumb.locations[1], handle_alert=True)
        view.flash.assert_no_error()

    @variable(alias='rest')
    def deny_request(self, reason):
        """Opens the specified request and deny it.
        Args:
            reason: Reason for denying the request.
            cancel: Whether to cancel the denial.
        """
        self.rest.action.deny(reason=reason)

    @deny_request.variant('ui')
    def deny_request_ui(self, reason, cancel=False):
        view = navigate_to(self, 'Deny')
        view.reason.fill(reason)
        if not cancel:
            view.submit.click()
        else:
            view.breadcrumb.click_location(view.breadcrumb.locations[1], handle_alert=True)
        view.flash.assert_no_error()

    @variable
    def remove_request(self, cancel=False):
        """Opens the specified request and deletes it - removes from UI
        Args:
            cancel: Whether to cancel the deletion.
        """
        if self.exists(method="ui"):
            view = navigate_to(self, 'Details')
            view.toolbar.delete.click(handle_alert=not cancel)

    @remove_request.variant("rest")
    def remove_request_rest(self):
        if "service" in self.rest.request_type:
            request = self.appliance.rest_api.collections.service_requests.find_by(id=self.rest.id)
            request[0].action.delete()
        else:
            raise NotImplementedError(
                f"{self.rest.request_type} does not support delete operation via REST"
            )

    @variable(alias='rest')
    def is_finished(self):
        """Helper function checks if a request is completed
        """
        self.update()
        return self.rest.request_state.title() in self.REQUEST_FINISHED_STATES

    @is_finished.variant('ui')
    def is_finished_ui(self):
        self.update(method='ui')
        return self.row.request_state.text in self.REQUEST_FINISHED_STATES

    @variable(alias='rest')
    def is_succeeded(self):
        return self.is_finished() and self.rest.status.title() == 'Ok'

    @is_succeeded.variant('ui')
    def is_succeeded_ui(self):
        return self.is_finished(method='ui') and self.row.status.text == 'Ok'

    def copy_request(self, values=None, cancel=False):
        """Copies the request  and edits if needed
        """
        view = navigate_to(self, 'Copy')
        view.form.fill(values)
        if not cancel:
            view.form.submit_button.click()
        else:
            view.cancel_button.click()
        view.flash.assert_no_error()
        # The way we identify request is a description which is based on vm_name,
        # no need returning Request obj if name is the same => raw request copy
        if 'catalog' in values and 'vm_name' in values['catalog']:
            return Request(self.parent, description=values['catalog']['vm_name'],
                           partial_check=True)

    def edit_request(self, values, cancel=False):
        """Opens the request for editing and saves or cancels depending on success.
        """
        view = navigate_to(self, 'Edit')
        if view.form.fill(values):
            if not cancel:
                view.form.submit_button.click()
                # TODO remove this hack for description update that anchors the request
                if values.get('Description'):
                    self.description = values['Description']
                    self.cells.update({'Description': self.description})
                self.update()
            else:
                view.cancel_button.click()
        else:
            logger.debug('Nothing was changed in current request')
        view.flash.assert_no_error()


@attr.s
class RequestCollection(BaseCollection):
    """The appliance collection of requests"""
    ENTITY = Request


class RequestsToolbar(View):
    """Toolbar on the requests view"""
    reload = Button(title='Refresh this page')


class RequestBasicView(BaseLoggedInPage):
    title = Text('//div[@id="main-content"]//h1')
    toolbar = View.nested(RequestsToolbar)

    @property
    def in_requests(self):
        return (
            self.logged_in_as_current_user
            and self.navigation.currently_selected == ['Services', 'Requests']
        )

    @View.nested
    class filter_by(View):  # noqa
        requester = BootstrapSelect(
            locator=(
                './/div[contains(@class, "requester")]'
                '/div[contains(@class, "bootstrap-select")]'
            )
        )
        # TODO: Add other available fields.
        apply = Button('Apply')
        reset = Button('Reset')


class RequestsView(RequestBasicView):
    table = Table(locator='//div[@id="gtl_div"]//table')
    paginator = PaginationPane()

    def find_request(self, cells, partial_check=False):
        """Finds the request and returns the row element
        Args:
            cells: Search data for the requests table.
            partial_check: If to use the ``__contains`` operator
        Returns: row
        """
        contains = '' if not partial_check else '__contains'
        column_list = self.table.attributized_headers
        cells = copy(cells)
        for key in list(cells):
            for column_name, column_text in column_list.items():
                if key == column_text:
                    cells[f'{column_name}{contains}'] = cells.pop(key)
                    break

        for _ in self.paginator.pages():
            rows = list(self.table.rows(**cells))
            if len(rows) == 0:
                # row not on this page, assume it has yet to appear
                # it might be nice to add an option to fail at this point
                continue
            elif len(rows) > 1:
                raise RequestException('Multiple requests with matching content found - '
                                       'be more specific!')
            else:
                # found the row!
                row = rows[0]
                logger.debug(' Request Message: %s', row.last_message.text)
                return row
        else:
            raise Exception("The request specified by {} not found!".format(str(cells)))

    @property
    def is_displayed(self):
        return self.in_requests and self.title.text == 'Requests'


class RequestDetailsToolBar(RequestsView):
    copy = Button(title='Copy original Request')
    edit = Button(title='Edit the original Request')
    delete = Button(title='Delete this Request')
    approve = Button(title='Approve this Request')
    deny = Button(title='Deny this Request')


class RequestDetailsView(RequestsView):

    @View.nested
    class details(View):  # noqa
        request_details = SummaryForm('Request Details')

    @View.nested
    class request(WaitTab):  # noqa
        TAB_NAME = 'Request'
        email = SummaryFormItem('Request Information', 'E-Mail')
        first_name = SummaryFormItem('Request Information', 'First Name')
        last_name = SummaryFormItem('Request Information', 'Last Name')
        notes = SummaryFormItem('Request Information', 'Notes')
        manager_name = SummaryFormItem('Manager', 'Name')

    @View.nested
    class purpose(WaitTab):  # noqa
        TAB_NAME = 'Purpose'
        apply_tags = BootstrapTreeview('all_tags_treebox')

    @View.nested
    class catalog(WaitTab):  # noqa
        TAB_NAME = 'Catalog'
        filter_template = SummaryFormItem('Select', 'Filter')
        name = SummaryFormItem('Select', 'Name')
        provision_type = SummaryFormItem('Select', 'Provision Type')
        linked_clone = Checkbox(id='service__linked_clone')
        vm_count = SummaryFormItem('Number of VMs', 'Count')
        instance_count = SummaryFormItem('Number of Instances', 'Count')
        vm_name = SummaryFormItem('Naming', 'VM Name')
        instance_name = SummaryFormItem('Naming', 'Instance Name')
        vm_description = SummaryFormItem('Naming', 'VM Description')

    @View.nested
    class environment(WaitTab):  # noqa
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
    class hardware(WaitTab):  # noqa
        num_cpus = SummaryFormItem('Hardware', 'Number of CPUS')
        memory = SummaryFormItem('Hardware', 'Startup Memory (MB)')
        dynamic_memory = SummaryFormItem('Hardware', 'Dynamic Memory')
        vm_limit_cpu = SummaryFormItem('VM Limits', 'CPU (%)')
        vm_reserve_cpu = SummaryFormItem('VM Reservations', 'CPU (%)')

    @View.nested
    class network(WaitTab):  # noqa
        vlan = SummaryFormItem('Network Adapter Information', 'vLan')

    @View.nested
    class properties(WaitTab):  # noqa
        instance_type = SummaryFormItem('Properties', 'Instance Type')
        boot_disk_size = SummaryFormItem('Properties', 'Boot Disk Size ')
        is_preemptible = Checkbox(name='hardware__is_preemptible')

    @View.nested
    class customize(WaitTab):  # noqa
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
    class schedule(WaitTab):  # noqa
        when_provision = SummaryFormItem('Schedule Info', 'When to Provision')
        stateless = Checkbox(name='shedule__stateless')
        power_on = SummaryFormItem('Lifespan', 'Power on virtual machines after creation')
        retirement = SummaryFormItem('Lifespan', 'Time until Retirement')
        retirement_warning = SummaryFormItem('Lifespan', 'Retirement Warning')

    @View.nested
    class volumes(WaitTab):  # noqa
        volume_name = SummaryFormItem('Volumes', 'Volume Name')
        volume_size = SummaryFormItem('Volumes', 'Size (gigabytes)')
        delete_on_terminate = Checkbox(name='volumes__delete_on_terminate_1')

    @property
    def is_displayed(self):
        expected_description = self.context['object'].rest.description
        return (
            self.in_requests and
            self.breadcrumb.locations[-1] == expected_description and
            self.title.text == expected_description
        )

    breadcrumb = BreadCrumb()
    toolbar = RequestDetailsToolBar()


class RequestApprovalView(RequestDetailsView):

    reason = Input(name='reason')
    submit = Button(title='Submit')
    cancel = Button(title="Cancel this provisioning request")

    @property
    def is_displayed(self):
        try:
            return (
                self.breadcrumb.locations[-1] == 'Request Approval' and
                self.breadcrumb.locations[-2] == self.context['object'].rest.description
            )
        except Exception:
            return False


class RequestDenialView(RequestDetailsView):

    reason = Input(name='reason')
    submit = Button(title='Submit')
    cancel = Button(title="Cancel this provisioning request")

    @property
    def is_displayed(self):
        try:
            return (
                self.breadcrumb.locations[-1] == 'Request Denial' and
                self.breadcrumb.locations[-2] == self.context['object'].rest.description
            )
        except Exception:
            return False


class RequestProvisionView(ProvisionView):

    @View.nested
    class form(BasicProvisionFormView):  # noqa
        submit_button = Button('Submit')  # Submit for 2nd page, tabular form
        cancel_button = Button('Cancel')

    @property
    def is_displayed(self):
        try:
            return self.breadcrumb.locations[-1] == self.context['object'].rest.description
        except Exception:
            return False


class RequestEditView(RequestProvisionView):
    # BZ 1726741 will impact the breadcrumb items
    is_displayed = displayed_not_implemented
    # @property
    # def is_displayed(self):
    #     try:
    #         return (
    #             self.breadcrumb.locations[-2] == self.context['object'].rest.description and
    #             self.breadcrumb.locations[-1] == 'Edit VM Provision')
    #     except Exception:
    #         return False


class RequestCopyView(RequestProvisionView):
    # BZ 1726741 will impact the breadcrumb items
    is_displayed = displayed_not_implemented
    # @property
    # def is_displayed(self):
    #     try:
    #         return (
    #             self.breadcrumb.locations[-2] == self.context['object'].rest.description and
    #             self.breadcrumb.locations[-1] == 'Copy of VM Provision Request')
    #     except Exception:
    #         return False


@navigator.register(RequestCollection, 'All')
class RequestAll(CFMENavigateStep):
    VIEW = RequestsView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Services', 'Requests')


@navigator.register(Request, 'Details')
class RequestDetails(CFMENavigateStep):
    VIEW = RequestDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        try:
            return self.prerequisite_view.table.row(description=self.obj.rest.description).click()
        except (NameError, TypeError):
            logger.warning('Exception caught, could not match Request')


@navigator.register(Request, 'Edit')
class EditRequest(CFMENavigateStep):
    VIEW = RequestEditView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        return self.prerequisite_view.toolbar.edit.click()


@navigator.register(Request, 'Copy')
class CopyRequest(CFMENavigateStep):
    VIEW = RequestCopyView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        return self.prerequisite_view.toolbar.copy.click()


@navigator.register(Request, 'Approve')
class ApproveRequest(CFMENavigateStep):
    VIEW = RequestApprovalView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        return self.prerequisite_view.toolbar.approve.click()


@navigator.register(Request, 'Deny')
class DenyRequest(CFMENavigateStep):
    VIEW = RequestDenialView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        return self.prerequisite_view.toolbar.deny.click()
