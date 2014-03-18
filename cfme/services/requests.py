from cfme.web_ui import SplitTable, paginator, toolbar
from utils.log import logger

request_list = SplitTable(
    ('//*[@id="list_grid"]//table[contains(@class, "hdr")]/tbody', 1),
    ('//*[@id="list_grid"]//table[contains(@class, "obj")]/tbody', 1)
)


def reload():
    toolbar.select('Reload')


def wait_for_request(cells):
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

    Returns:

    """
    for page in paginator.pages():
        try:
            # found the row!
            row, = request_list.find_rows_by_cells(cells)
            logger.debug(' Request Message: %s' % row.last_message.text)
            break
        except ValueError:
            # row not on this page, assume it has yet to appear
            # it might be nice to add an option to fail at this point
            continue
    else:
        # Request not found at all, can't continue
        return False

    assert row.status.text != 'Error'
    if row.request_state.text == 'Finished':
        return row
    else:
        return False
