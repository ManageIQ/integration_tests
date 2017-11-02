# -*- coding: utf-8 -*-
import random
import itertools
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.image import Image as ApiImage

from cfme.common import (WidgetasticTaggable, PolicyProfileAssignable,
                         TagPageView)
from cfme.containers.provider import (Labelable, navigate_and_get_rows,
    ContainerObjectAllBaseView, ContainerObjectDetailsBaseView, click_row,
    LoadDetailsMixin, refresh_and_navigate, ContainerObjectDetailsEntities)
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.utils.appliance import Navigatable
from cfme.configure import tasks
from cfme.utils.wait import wait_for, TimedOutError
from widgetastic_manageiq import SummaryTable
from widgetastic.widget import View


class ImageAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Container Images"


class ImageDetailsView(ContainerObjectDetailsBaseView):
    @View.nested
    class entities(ContainerObjectDetailsEntities):  # noqa
        configuration = SummaryTable(title='Configuration')
        compliance = SummaryTable(title='Compliance')


class Image(WidgetasticTaggable, Labelable, Navigatable, LoadDetailsMixin, PolicyProfileAssignable):

    PLURAL = 'Container Images'
    all_view = ImageAllView
    details_view = ImageDetailsView

    def __init__(self, name, image_id, provider, appliance=None):
        self.name = name
        self.id = image_id
        self.provider = provider
        Navigatable.__init__(self, appliance=appliance)

    @cached_property
    def mgmt(self):
        return ApiImage(self.provider.mgmt, self.name, self.sha256)

    @cached_property
    def sha256(self):
        return self.id.split('@')[-1]

    def perform_smartstate_analysis(self, wait_for_finish=False, timeout='7M'):
        """Performing SmartState Analysis on this Image
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        # TODO: Modify accordingly once there is FlashMessages.assert_massage_contains()
        assert filter(lambda m: 'Analysis successfully initiated' in m.text, view.flash.messages)
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
        view = navigate_to(self, 'Details')
        original_state = self.compliance_status
        view.toolbar.policy.item_select("Check Compliance of Last Known Configuration",
                                        handle_alert=True)
        view.flash.assert_no_error()
        if wait_for_finish:
            wait_for(
                lambda: self.compliance_status != original_state, num_sec=timeout, delay=5,
                message='compliance state of {} still matches {}'
                        .format(self.name, original_state)
            )
        return self.compliant

    @property
    def compliance_status(self):
        view = refresh_and_navigate(self, 'Details')
        return view.entities.compliance.read().get('Status').strip()

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


@navigator.register(Image, 'All')
class All(CFMENavigateStep):
    VIEW = ImageAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Images')

    def resetter(self):
        # Reset view and selection
        self.view.toolbar.view_selector.select("List View")
        self.view.paginator.check_all()
        self.view.paginator.uncheck_all()


@navigator.register(Image, 'Details')
class Details(CFMENavigateStep):
    VIEW = ImageDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        click_row(self.prerequisite_view,
            provider=self.obj.provider.name, id=self.obj.id)


@navigator.register(Image, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
