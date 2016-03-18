# -*- coding: utf-8 -*-
from contextlib import contextmanager
from cfme.exceptions import RequestException
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import Input, Region, SplitTable, Table, fill, flash, paginator, toolbar
from utils import version
from utils.log import logger

REQUEST_FINISHED_STATES = {'Migrated', 'Finished'}

buttons = Region(
    locators=dict(
        approve="//*[@title='Approve this Request']/img",
        deny="//*[@title='Deny this Request']/img",
        copy="//*[@title='Copy original Request']/img",
        edit="//*[@title='Edit the original Request']/img",
        delete="//*[@title='Delete this Request']/img",
        submit="//span[@id='buttons_on']/a[@title='Submit']",
        cancel="//a[@title='Cancel']",
    )
)


fields = Region(
    locators=dict(
        reason=Input("reason"),
        request_list={
            version.LOWEST: SplitTable(
                ('//*[@id="list_grid"]//table[contains(@class, "hdr")]/tbody', 1),
                ('//*[@id="list_grid"]//table[contains(@class, "obj")]/tbody', 1)),
            "5.5.0.8": Table('//*[@id="list_grid"]/table'),
        }
    )
)


def reload():
    toolbar.select('Reload')


def approve(reason, cancel=False):
    """Approve currently opened request

    Args:
        reason: Reason for approving the request.
        cancel: Whether to cancel the approval.
    """
    sel.wait_for_element(buttons.approve)
    sel.click(buttons.approve)
    sel.wait_for_element(fields.reason)
    fill(fields.reason, reason)
    sel.click(buttons.submit if not cancel else buttons.cancel)
    flash.assert_no_errors()


def approve_request(cells, reason, cancel=False):
    """Open the specified request and approve it.

    Args:
        cells: Search data for the requests table.
        reason: Reason for approving the request.
        cancel: Whether to cancel the approval.

    Raises:
        RequestException: :py:class:`cfme.exceptions.RequestException` if the request was not found
    """
    if not go_to_request(cells):
        raise RequestException("Request with identification {} not found!".format(str(cells)))
    approve(reason, cancel)


def deny(reason, cancel=False):
    """Deny currently opened request

    Args:
        reason: Reason for denying the request.
        cancel: Whether to cancel the denial.
    """
    sel.click(buttons.deny)
    fill(fields.reason, reason)
    sel.click(buttons.submit if not cancel else buttons.cancel)
    flash.assert_no_errors()


def deny_request(cells, reason, cancel=False):
    """Open the specified request and deny it.

    Args:
        cells: Search data for the requests table.
        reason: Reason for denying the request.
        cancel: Whether to cancel the denial.

    Raises:
        RequestException: :py:class:`cfme.exceptions.RequestException` if the request was not found
    """
    if not go_to_request(cells):
        raise RequestException("Request with identification {} not found!".format(str(cells)))
    deny(reason, cancel)


def delete(cancel=False):
    """Delete currently opened request

    Args:
        cancel: Whether to cancel the deletion.
    """
    sel.wait_for_element(buttons.delete)
    sel.click(buttons.delete, wait_ajax=False)
    sel.handle_alert(cancel)
    sel.wait_for_ajax()
    flash.assert_no_errors()


def delete_request(cells, cancel=False):
    """Open the specified request and delete it.

    Args:
        cells: Search data for the requests table.
        cancel: Whether to cancel the deletion.

    Raises:
        RequestException: :py:class:`cfme.exceptions.RequestException` if the request was not found
    """
    if not go_to_request(cells):
        raise RequestException("Request with identification {} not found!".format(str(cells)))
    delete(cancel)


def wait_for_request(cells, partial_check=False):
    """helper function checks if a request is complete

    After finding the request's row using the ``cells`` argument, this will wait for a request to
    reach the 'Finished' state and return it. In the event of an 'Error' state, it will raise an
    AssertionError, for use with ``pytest.raises``, if desired.

    Args:
        cells: A dict of cells use to identify the request row to inspect in the
            :py:attr:`request_list` Table. See :py:meth:`cfme.web_ui.Table.find_rows_by_cells`
            for more.

    Usage:

        # Filter on the "Description" column
        description = 'Provision from [%s] to [%s]' % (template_name, vm_name)
        cells = {'Description': description}

        # Filter on the "Request ID" column
        # Text must match exactly, you can use "{:,}".format(request_id) to add commas if needed.
        request_id = '{:,}'.format(1000000000001)  # Becomes '1,000,000,000,001', as in the table
        cells = {'Request ID': request_id}

        # However you construct the cells dict, pass it to wait_for_request
        # Provisioning requests often take more than 5 minutes but less than 10.
        wait_for(wait_for_request, [cells], num_sec=600)

    Raises:
        AssertionError: if the matched request has status 'Error'
        RequestException: if multiple matching requests were found

    Returns:
         The matching :py:class:`cfme.web_ui.Table.Row` if found, ``False`` otherwise.
    """
    for page in paginator.pages():
        # We check only for the SplitTable. Can't think of better detection.
        if version.current_version() < "5.5.0.8"\
                and sel.elements(fields.request_list._header_loc) and\
                not sel.is_displayed(fields.request_list):
            # The table exists but it is hidden - no cells
            return False
        results = fields.request_list.find_rows_by_cells(cells, partial_check)
        if len(results) == 0:
            # row not on this page, assume it has yet to appear
            continue
        elif len(results) > 1:
            raise RequestException(
                'Multiple requests with matching content found - be more specific!'
            )
        else:
            # found the row!
            row = results[0]
            logger.debug(' Request Message: %s', row.last_message.text)
            break
    else:
        # Request not found at all, can't continue
        return False

    if row.request_state.text in REQUEST_FINISHED_STATES:
        return row
    else:
        return False


def debug_requests():
    logger.debug('Outputting current requests')
    for page in paginator.pages():
        for row in fields.request_list.rows():
            logger.debug(' %s', row)


def find_request(cells):
    """Finds the request and opens the page

    See :py:func:`wait_for_request` for futher details.

    Args:
        cells: Search data for the requests table.
    Returns: Success of the action.
    """
    sel.force_navigate("services_requests")
    for page in paginator.pages():
        try:
            # found the row!
            row, = fields.request_list.find_rows_by_cells(cells)
            return True
        except ValueError:
            # row not on this page, assume it has yet to appear
            # it might be nice to add an option to fail at this point
            continue
    else:
        # Request not found at all, can't continue
        return False


def go_to_request(cells):
    """Finds the request and opens the page

    See :py:func:`wait_for_request` for futher details.

    Args:
        cells: Search data for the requests table.
    Returns: Success of the action.
    """
    sel.force_navigate("services_requests")
    for page in paginator.pages():
        try:
            # found the row!
            row, = fields.request_list.find_rows_by_cells(cells)
            sel.click(row)
            return True
        except ValueError:
            # row not on this page, assume it has yet to appear
            # it might be nice to add an option to fail at this point
            continue
    else:
        # Request not found at all, can't continue
        return False


@contextmanager
def copy_request(cells):
    """Context manager that opens the request for editing and saves or cancels depending on success.

    Args:
        cells: Search data for the requests table.
    """
    if not go_to_request(cells):
        raise Exception("The requst specified by {} not found!".format(str(cells)))
    sel.wait_for_element(buttons.copy)  # It is glitching here ...
    sel.click(buttons.copy)
    try:
        yield
    except Exception:
        sel.click(buttons.cancel)
        raise
    else:
        from cfme.provisioning import provisioning_form
        btn = provisioning_form.submit_copy_button
        sel.wait_for_element(btn)
        sel.click(btn)
        flash.assert_no_errors()


@contextmanager
def edit_request(cells):
    """Context manager that opens the request for editing and saves or cancels depending on success.

    Args:
        cells: Search data for the requests table.
    """
    if not go_to_request(cells):
        raise Exception("The requst specified by {} not found!".format(str(cells)))
    sel.wait_for_element(buttons.edit)  # It is glitching here ...
    sel.click(buttons.edit)
    from cfme.provisioning import provisioning_form
    try:
        yield provisioning_form
    except Exception as e:
        logger.exception(e)
        sel.click(buttons.cancel)
        raise
    else:
        sel.click(provisioning_form.submit_copy_button)
        flash.assert_no_errors()
