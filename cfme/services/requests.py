# -*- coding: utf-8 -*-
from contextlib import contextmanager
from functools import partial
from navmazing import NavigateToAttribute, NavigateToSibling
from widgetastic.widget import Text, Table
from widgetastic_manageiq import BreadCrumb
from widgetastic_patternfly import Button, View, Input, Tab

from cfme import BaseLoggedInPage
from cfme.exceptions import RequestException
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, PagedTable, flash, paginator, toolbar, match_location)
from utils.log import logger
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


"""
buttons = Region(
    locators=dict(
        approve="//*[@title='Approve this Request']",
        deny="//*[@title='Deny this Request']",
        copy="//*[@title='Copy original Request']",
        edit="//*[@title='Edit the original Request']",
        delete="//*[@title='Delete this Request']",
        submit="//span[@id='buttons_on']/a[@title='Submit']",
        cancel="//a[@title='Cancel']",
    )
)
"""
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


# TODO Refactor these module methods and their callers for a proper request class
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
        """helper function checks if a request is complete

        Raises:
            RequestException: if multiple matching requests were found

        Returns:
             The matching :py:class:`cfme.web_ui.Table.Row` if found, ``False`` otherwise.
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
    # TODO Add Request details elements
    @View.nested
    class details(View):
        # Form ? or just test values
        pass

    @View.nested
    class request(Tab):
        pass

    @View.nested
    class purpose(Tab):
        pass

    @View.nested
    class catalog(Tab):
        pass

    @View.nested
    class environment(Tab):
        pass

    @View.nested
    class hardware(Tab):
        pass

    @View.nested
    class network(Tab):
        pass

    @View.nested
    class properties(Tab):
        pass

    @View.nested
    class customize(Tab):
        pass

    @View.nested
    class schedule(Tab):
        pass

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
