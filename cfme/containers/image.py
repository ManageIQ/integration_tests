# -*- coding: utf-8 -*-
import attr
from cached_property import cached_property

from navmazing import NavigateToSibling, NavigateToAttribute
from wrapanapi.containers.image import Image as ApiImage

from cfme.common import (WidgetasticTaggable, PolicyProfileAssignable,
                         TagPageView)
from cfme.containers.provider import (Labelable,
                                      ContainerObjectAllBaseView,
                                      ContainerObjectDetailsBaseView, LoadDetailsMixin,
                                      refresh_and_navigate, ContainerObjectDetailsEntities,
                                      GetRandomInstancesMixin)
from cfme.utils.appliance.implementations.ui import CFMENavigateStep, navigator, navigate_to
from cfme.configure import tasks
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.utils.wait import wait_for, TimedOutError
from widgetastic_manageiq import SummaryTable, BaseEntitiesView
from widgetastic.widget import View
from cfme.utils.providers import get_crud_by_name


class ImageAllView(ContainerObjectAllBaseView):
    SUMMARY_TEXT = "Container Images"

    # ProviderEntity has its own fields, image view should rather use BaseEntity instead
    including_entities = View.include(BaseEntitiesView, use_parent=True)


class ImageDetailsView(ContainerObjectDetailsBaseView):
    @View.nested
    class entities(ContainerObjectDetailsEntities):  # noqa
        configuration = SummaryTable(title='Configuration')
        compliance = SummaryTable(title='Compliance')


@attr.s
class Image(BaseEntity, WidgetasticTaggable, Labelable, LoadDetailsMixin, PolicyProfileAssignable):

    PLURAL = 'Container Images'
    all_view = ImageAllView
    details_view = ImageDetailsView

    name = attr.ib()
    id = attr.ib()
    provider = attr.ib()

    @cached_property
    def mgmt(self):
        return ApiImage(self.provider.mgmt, self.name, self.sha256)

    @cached_property
    def sha256(self):
        return self.id.split('@')[-1]

    def perform_smartstate_analysis(self, wait_for_finish=False, timeout='7M'):
        """Performing SmartState Analysis on this Image
        """
        # task_name change from str to regular expression pattern following Bugzilla Bug 1483590
        # task name will contain also Image name
        # the str compile on tasks module
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        # TODO: Modify accordingly once there is FlashMessages.assert_massage_contains()
        assert filter(lambda m: 'Analysis successfully initiated' in m.text, view.flash.messages)
        if wait_for_finish:
            try:
                wait_for(tasks.is_analysis_finished,
                         func_kwargs={'name': '(?i)(Container Image.*)',
                                      'task_type': 'container'},
                         timeout=timeout,
                         fail_func=self.appliance.server.browser.refresh)
            except TimedOutError:
                raise TimedOutError('Timeout exceeded, Waited too much time for SSA to finish ({}).'
                                    .format(timeout))

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


@attr.s
class ImageCollection(GetRandomInstancesMixin, BaseCollection):
    """Collection object for :py:class:`Image`."""

    ENTITY = Image

    def all(self):
        # container_images has ems_id, join with ext_mgmgt_systems on id for provider name
        image_table = self.appliance.db.client['container_images']
        ems_table = self.appliance.db.client['ext_management_systems']
        image_query = (
            self.appliance.db.client.session
                .query(image_table.name, image_table.image_ref, ems_table.name)
                .join(ems_table, image_table.ems_id == ems_table.id))
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            image_query = image_query.filter(ems_table.name == provider.name)
        images = []
        for name, image_ref, ems_name in image_query.all():
            images.append(self.instantiate(name=name, id=image_ref,
                                           provider=provider or get_crud_by_name(ems_name)))
        return images


@navigator.register(ImageCollection, 'All')
class All(CFMENavigateStep):
    VIEW = ImageAllView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Images')

    def resetter(self):
        # Reset view and selection
        self.view.entities.search.clear_simple_search()
        self.view.toolbar.view_selector.select("List View")


@navigator.register(Image, 'Details')
class Details(CFMENavigateStep):
    VIEW = ImageDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(provider=self.obj.provider.name,
                                                   use_search=True, name=self.obj.name,
                                                   id=self.obj.id).click()


@navigator.register(Image, 'EditTags')
class ImageRegistryEditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
