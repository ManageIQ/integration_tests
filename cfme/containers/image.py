# -*- coding: utf-8 -*-
from functools import partial
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from widgetastic_patternfly import Dropdown
from wrapanapi.containers.image import Image as ApiImage

from cfme.common import SummaryMixin, Taggable, PolicyProfileAssignable
from cfme.containers.provider import Labelable, navigate_and_get_rows,\
    ContainerObjectAllBaseView
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import toolbar as tb, CheckboxTable, match_location, InfoBlock,\
    flash, PagedTable
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.appliance import Navigatable
from cfme.configure import tasks
from cfme.utils.wait import wait_for, TimedOutError

list_tbl = CheckboxTable(table_locator="//div[@id='list_grid']//table")
paged_tbl = PagedTable(table_locator="//div[@id='list_grid']//table")


match_page = partial(match_location, controller='container_image',
                     title='Images')


class Image(Taggable, Labelable, SummaryMixin, Navigatable, PolicyProfileAssignable):

    PLURAL = 'Container Images'

    def __init__(self, name, image_id, provider, appliance=None):
        self.name = name
        self.id = image_id
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

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

    @classmethod
    def get_random_instances(cls, provider, count=1, appliance=None, docker_only=False):
        """Generating random instances. (docker_only: means for docker images only)"""
        # Grab the images from the UI since we have no way to calculate the name by API attributes
        rows = navigate_and_get_rows(provider, cls, count=1000)
        if docker_only:
            docker_image_ids = [img.id for img in provider.mgmt.list_docker_image()]
            rows = filter(lambda r: r.id.text.split('@')[-1] in docker_image_ids,
                          rows)
        random.shuffle(rows)
        return [cls(row.name.text, row.id.text, provider, appliance=appliance)
                for row in itertools.islice(rows, count)]

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


@navigator.register(Image, 'All')
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
    prerequisite = NavigateToSibling('All')

    def am_i_here(self):
        return match_page(summary='{} (Summary)'.format(self.obj.name))

    def step(self):
        tb.select('List View')
        sel.click(paged_tbl.find_row_by_cell_on_all_pages({'Provider': self.obj.provider.name,
                                                           'Id': self.obj.id}))
