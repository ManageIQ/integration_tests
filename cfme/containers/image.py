# -*- coding: utf-8 -*-
from functools import partial
import attr
from cached_property import cached_property

from navmazing import NavigateToAttribute
from widgetastic_patternfly import Dropdown
from wrapanapi.containers.image import Image as ApiImage

from cfme.common import SummaryMixin, Taggable, PolicyProfileAssignable
from cfme.containers.provider import Labelable, ContainerObjectAllBaseView
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable, match_location, InfoBlock,\
    flash, PagedTable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.log import logger
from cfme.configure import tasks
from cfme.utils.wait import wait_for, TimedOutError
from cfme.modeling.base import BaseCollection, BaseEntity

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


match_page = partial(match_location, controller='container_image',
                     title='Images')


@attr.s
class Image(BaseEntity, Taggable, Labelable, SummaryMixin, PolicyProfileAssignable):

    PLURAL = 'Container Images'

    name = attr.ib()
    id = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiImage(self.provider.mgmt, self.name, self.sha256)

    # TODO: remove load_details and dynamic usage from cfme.common.Summary when nav is more complete
    def load_details(self, refresh=False):
        navigate_to(self, 'Details')
        if refresh:
            tb.refresh()

    def get_detail(self, *ident):
        """ Gets details from the details infoblock
        Args:
            *ident: Table name and Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the summary's value.
        """
        navigate_to(self, 'Details')
        return InfoBlock.text(*ident)

    @cached_property
    def sha256(self):
        return self.id.split('@')[-1]

    def perform_smartstate_analysis(self, wait_for_finish=False, timeout='7M'):
        """Performing SmartState Analysis on this Image
        """
        navigate_to(self, 'Details')
        tb.select('Configuration', 'Perform SmartState Analysis', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_contain('Analysis successfully initiated')
        if wait_for_finish:
            try:
                tasks.wait_analysis_finished('Container image analysis',
                                             'container', timeout=timeout)
            except TimedOutError:
                raise TimedOutError('Timeout exceeded, Waited too much time for SSA to finish ({}).'
                                    .format(timeout))

    def check_compliance(self, wait_for_finish=True, timeout=240):
        """Initiates compliance check and waits for it to finish."""
        navigate_to(self, 'Details')
        original_state = self.compliance_status
        tb.select('Policy',
                  "Check Compliance of Last Known Configuration",
                  invokes_alert=True)
        sel.handle_alert()
        flash.assert_no_errors()
        if wait_for_finish:
            wait_for(
                lambda: self.compliance_status != original_state,
                num_sec=timeout, delay=5, fail_func=sel.refresh,
                message='compliance state of {} still matches {}'
                        .format(self.name, original_state)
            )
        return self.compliant

    @property
    def compliance_status(self):
        self.summary.reload()
        return self.summary.compliance.status.value.strip()

    @property
    def compliant(self):
        """Check if the image is compliant

        Returns:
            :py:class:`NoneType` if the image was never verified, otherwise :py:class:`bool`
        """
        text = self.compliance_status.lower()
        if text == "never verified":
            return None
        elif text.startswith("non-compliant"):
            return False
        elif text.startswith("compliant"):
            return True
        else:
            raise ValueError("{} is not a known state for compliance".format(text))


class ImageAllView(ContainerObjectAllBaseView):
    TITLE_TEXT = "Container Images"
    configuration = Dropdown('Configuration')


@attr.s
class ImageCollection(BaseCollection):
    ENTITY = Image

    # TODO: Benny you have to make this function work with the new structure.
    # Image rows is not relevant anymore,
    # you have to select few random rows and than start SSA from the toolbar
    def perform_smartstate_analysis(self, image_rows, wait_for_finish=False, timeout='20M'):
        """Performing SmartState Analysis on this Image
        """

        # task_name change from str to regular expression pattern following Bugzilla Bug 1483590
        # task name will contain also Image name
        # the str compile on tasks module
        task_name = 'Container image.*'
        task_type = 'container'
        num_of_tasks = len(image_rows)
        images_view = navigate_to(self, 'All')
        images_view.table.sort_by('Name', 'asc')
        images_view.check_rows(image_rows)
        images_view.select_configuration('Perform SmartState Analysis', handle_alert=True)
        for row in image_rows:
            flash.assert_message_contain('"{}": Analysis successfully initiated'
                                         .format(row.name.text))
        if wait_for_finish:
            try:
                # check all tasks state finished
                num_of_finished_tasks = tasks.wait_analysis_finished(task_name,
                                                                     task_type, num_of_tasks,
                                                                     timeout=timeout)
                logger.info('"{}": Images SSA tasks finished.'.format(num_of_finished_tasks))

                # check all task passed successfully with no error
                if tasks.are_all_analysis_finished(task_name, num_of_tasks, task_type,
                                                   silent_failure=True,
                                                   clear_tasks_after_success=False):
                    logger.info('"{}": Images SSA tasks finished with no error message'
                                .format(num_of_tasks))
                    return True
                else:
                    logger.error('Some Images SSA tasks finished with error message,'
                                 ' see logger for more details.')
                    return False

            except TimedOutError:
                raise TimedOutError('Timeout exceeded, Waited too much time for SSA to finish ({}).'
                                    .format(timeout))


@navigator.register(ImageCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ImageAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Images')

    def resetter(self):
        from cfme.web_ui import paginator
        tb.select('Grid View')
        paginator.check_all()
        paginator.uncheck_all()


@navigator.register(Image, 'Details')
class Details(CFMENavigateStep):
    prerequisite = NavigateToAttribute("parent", 'All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Provider': self.obj.provider.name,
                                                           'Id': self.obj.id}))
