import attr
from cached_property import cached_property
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.widget import View

from cfme.common import PolicyProfileAssignable
from cfme.common import Taggable
from cfme.common import TaggableCollection
from cfme.common import TagPageView
from cfme.containers.provider import ContainerObjectAllBaseView
from cfme.containers.provider import ContainerObjectDetailsBaseView
from cfme.containers.provider import ContainerObjectDetailsEntities
from cfme.containers.provider import GetRandomInstancesMixin
from cfme.containers.provider import Labelable
from cfme.containers.provider import LoadDetailsMixin
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.log import logger
from cfme.utils.providers import get_crud_by_name
from cfme.utils.wait import TimedOutError
from cfme.utils.wait import wait_for
from widgetastic_manageiq import BaseEntitiesView
from widgetastic_manageiq import SummaryTable


class ImageAllView(ContainerObjectAllBaseView):
    """Container Images All view"""
    SUMMARY_TEXT = "Container Images"

    # ProviderEntity has its own fields, image view should rather use BaseEntity instead
    including_entities = View.include(BaseEntitiesView, use_parent=True)


class ImageDetailsView(ContainerObjectDetailsBaseView):
    """Container Images Detail view"""
    SUMMARY_TEXT = "Container Images"

    @View.nested
    class entities(ContainerObjectDetailsEntities):  # noqa
        configuration = SummaryTable(title='Configuration')
        compliance = SummaryTable(title='Compliance')


@attr.s
class Image(BaseEntity, Taggable, Labelable, LoadDetailsMixin, PolicyProfileAssignable):

    PLURAL = 'Container Images'
    all_view = ImageAllView
    details_view = ImageDetailsView

    name = attr.ib()
    id = attr.ib()
    provider = attr.ib()

    @cached_property
    def sha256(self):
        return self.id.split('@')[-1]

    @property
    def last_scan_attempt_on(self):
        """ Get 'Last Scan Attempt On' property for OCP Image.

            Returns:
                datetime or None.
        """
        try:
            # API does not accept a unicode string, setting the image name to a string
            return (self.appliance.rest_api.collections.container_images.
                    find_by(image_ref=str(self.id)).resources[0].last_scan_attempt_on)
        # If no scan has been performed on the image, it will return an AttributeError
        except AttributeError:
            return None

    def perform_smartstate_analysis(self, wait_for_finish=False, timeout='20M'):
        """Performing SmartState Analysis on this Image
        """
        # task_name change from str to regular expression pattern following Bugzilla Bug 1483590
        # task name will contain also Image name
        # the str compile on tasks module
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Perform SmartState Analysis', handle_alert=True)
        view.flash.assert_message('Analysis successfully initiated', partial=True)
        if wait_for_finish:
            try:
                task = self.appliance.collections.tasks.instantiate(
                    name=f"Container Image Analysis: '{self.name}'", tab='AllTasks')
                task.wait_for_finished(timeout=timeout)
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
        view = navigate_to(self, 'Details', force=True)
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
            raise ValueError(f"{text} is not a known state for compliance")

    def scan(self):
        """ Start SmartState Analysis Scan of OCP Image.

            Returns:
                API response.
        """

        # API does not accept a unicode string, setting the image name to a string
        return (self.appliance.rest_api.collections.container_images.
                find_by(image_ref=str(self.id)).resources[0].action.scan())


@attr.s
class ImageCollection(GetRandomInstancesMixin, BaseCollection, PolicyProfileAssignable,
                      TaggableCollection):
    """Collection object for :py:class:`Image`."""

    ENTITY = Image

    def all(self):
        # container_images has ems_id, join with ext_mgmgt_systems on id for provider name
        # TODO Update to use REST API instead of DB queries
        image_table = self.appliance.db.client['container_images']
        ems_table = self.appliance.db.client['ext_management_systems']
        image_registry_table = self.appliance.db.client['container_image_registries']
        image_query = (
            self.appliance.db.client.session
                .query(image_table.name, image_table.image_ref, ems_table.name,
                       image_registry_table.name)
                .join(ems_table, image_table.ems_id == ems_table.id)
                .join(image_registry_table,
                      image_table.container_image_registry_id == image_registry_table.id))
        if self.filters.get('archived'):
            image_query = image_query.filter(image_table.deleted_on.isnot(None))
        if self.filters.get('active'):
            image_query = image_query.filter(image_table.deleted_on.is_(None))
        # filter for containers images from openShift local redhat registry
        if self.filters.get('redhat_registry'):
            image_query = image_query.filter(
                image_registry_table.name.contains("registry.access.redhat.com")
            )
        provider = None
        # filtered
        if self.filters.get('provider'):
            provider = self.filters.get('provider')
            image_query = image_query.filter(ems_table.name == provider.name)
        images = []
        for name, image_ref, ems_name, _ in image_query.all():
            images.append(self.instantiate(name=name, id=image_ref,
                                           provider=provider or get_crud_by_name(ems_name)))
        return images

    def check_compliance_multiple_images(self, image_entities, check_on_entity=True, timeout=240):
        """Initiates compliance check and waits for it to finish on several Images.

        Args:
            image_entities: list of Image entities that need to perform compliance check on them
            check_on_entity (bool): check the compliance status on the entity summary view if True,
                                    only run compliance otherwise.
            timeout (seconds): time for waiting for compliance status
        """

        # Chose Check Compliance of Last Known Configuration
        images_view = navigate_to(self, 'All')
        self.check_image_entities(image_entities)
        wait_for(lambda: images_view.toolbar.policy.is_enabled, num_sec=5,
                 message='Policy drop down menu is disabled after checking some Images')
        images_view.toolbar.policy.item_select('Check Compliance of Last Known Configuration',
                                  handle_alert=True)
        images_view.flash.assert_no_error()

        # Verify Image summary
        if check_on_entity:
            for image_instance in image_entities:
                original_state = 'never verified'
                try:
                    wait_for(
                        lambda: image_instance.compliance_status.lower() != original_state,
                        num_sec=timeout, delay=5,
                        message='compliance state of Image ID, "{}", still matches {}'
                                .format(image_instance.id, original_state)
                    )
                except TimedOutError:
                    logger.error('compliance state of Image ID, "{}", is {}'
                                 .format(image_instance.id, image_instance.compliance_status))
                    raise TimedOutError('Timeout exceeded, Waited too much'
                                        ' time for check Compliance finish ({}).'.format(timeout))

    def check_image_entities(self, image_entities):
        """check rows on Container Images table."""
        images_view = navigate_to(self, 'All', use_resetter=False)
        images_view.paginator.set_items_per_page(1000)
        conditions = []
        for image_entity in image_entities:
            conditions.append({'id': image_entity.id})
        entities = images_view.entities.apply(func=lambda e: e.ensure_checked(),
                                              conditions=conditions)
        return entities

    def perform_smartstate_analysis_multiple_images(
            self, image_entities, wait_for_finish=False, timeout='20M'):
        """Performing SmartState Analysis on this Image
        """

        # task_name change from str to regular expression
        # the str compile on tasks module
        image_entities_names = []
        images_view = navigate_to(self, 'All')
        self.check_image_entities(image_entities)

        images_view.toolbar.configuration.item_select(
            'Perform SmartState Analysis', handle_alert=True)
        for image_entity in image_entities:
            image_entities_names.append(f"Container Image Analysis: '{image_entity.name}'")
            images_view.flash.assert_success_message(
                f'"{image_entity.name}": Analysis successfully initiated', partial=True
            )

        if wait_for_finish:
            try:
                col = self.appliance.collections.tasks.filter({'tab': 'AllTasks'})
                col.wait_for_finished(5, timeout, *image_entities_names)

                # check all task passed successfully with no error
                if col.is_successfully_finished(True, *image_entities_names):
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

    def step(self, *args, **kwargs):
        self.prerequisite_view.navigation.select('Compute', 'Containers', 'Container Images')

    def resetter(self, *args, **kwargs):
        # Reset view and selection
        self.view.entities.search.clear_simple_search()
        self.view.toolbar.view_selector.select("List View")


@navigator.register(Image, 'Details')
class Details(CFMENavigateStep):
    VIEW = ImageDetailsView
    prerequisite = NavigateToAttribute('parent', 'All')

    def step(self, *args, **kwargs):
        search_visible = self.prerequisite_view.entities.search.is_displayed
        self.prerequisite_view.entities.get_entity(provider=self.obj.provider.name,
                                                   surf_pages=not search_visible,
                                                   use_search=search_visible, name=self.obj.name,
                                                   id=self.obj.id).click()


@navigator.register(Image, 'EditTags')
class EditTags(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
