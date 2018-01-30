# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException, RowNotFound
from widgetastic_patternfly import BootstrapSelect, Button, CheckableBootstrapTreeview
from widgetastic.widget import Table, Text, View

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.configure.configuration.region_settings import Category, Tag
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from widgetastic_manageiq import BaseNonInteractiveEntitiesView, BreadCrumb


class ManagePoliciesView(BaseLoggedInPage):
    """
    Manage policies page
    """
    policy_profiles = CheckableBootstrapTreeview(tree_id='protectbox')
    breadcrumb = BreadCrumb()  # some views have breadcrumb, some not
    entities = View.nested(BaseNonInteractiveEntitiesView)
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class PolicyProfileAssignable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign Policy Profiles
    """

    @property
    def assigned_policy_profiles(self):
        try:
            return self._assigned_policy_profiles
        except AttributeError:
            self._assigned_policy_profiles = set([])
            return self._assigned_policy_profiles

    def assign_policy_profiles(self, *policy_profile_names):
        """ Assign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        map(self.assigned_policy_profiles.add, policy_profile_names)
        self._assign_unassign_policy_profiles(True, *policy_profile_names)

    def unassign_policy_profiles(self, *policy_profile_names):
        """ Unssign Policy Profiles to this object.

        Args:
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
        """
        for pp_name in policy_profile_names:
            try:
                self.assigned_policy_profiles.remove(pp_name)
            except KeyError:
                pass
        self._assign_unassign_policy_profiles(False, *policy_profile_names)

    def _assign_unassign_policy_profiles(self, assign, *policy_profile_names):
        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles` and :py:func:`assign_policy_profiles`

        Args:
            assign: Wheter to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
        """
        view = navigate_to(self, 'ManagePoliciesFromDetails')
        for policy_profile in policy_profile_names:
            if assign:

                view.policy_profiles.check_node(policy_profile)
            else:
                view.policy_profiles.uncheck_node(policy_profile)
        view.save.click()
        details_view = self.create_view(navigator.get_class(self, 'Details').VIEW)
        details_view.flash.assert_no_error()


@navigator.register(PolicyProfileAssignable, 'ManagePoliciesFromDetails')
class ManagePoliciesFromDetails(CFMENavigateStep):
    VIEW = ManagePoliciesView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


@navigator.register(PolicyProfileAssignable, 'ManagePolicies')
class ManagePolicies(CFMENavigateStep):
    VIEW = ManagePoliciesView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).check()
        self.prerequisite_view.toolbar.policy.item_select('Manage Policies')


class TagPageView(BaseLoggedInPage):
    """Class represents common tag page in CFME UI"""
    title = Text('#explorer_title_text')
    table_title = Text('//div[@id="tab_div"]/h3')

    @View.nested
    class form(View):  # noqa
        tags = Table("//div[@id='assignments_div']//table")
        tag_category = BootstrapSelect(id='tag_cat')
        tag_name = BootstrapSelect(id='tag_add')
        entities = View.nested(BaseNonInteractiveEntitiesView)
        save = Button('Save')
        reset = Button('Reset')
        cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return (
            self.table_title.text == 'Tag Assignment' and
            self.form.tags.is_displayed
        )


class WidgetasticTaggable(object):
    """
    This class can be inherited by any class that honors tagging.
    Class should have following

    * 'Details' navigation
    * 'Details' view should have entities.smart_management SummaryTable widget
    * 'EditTags' navigation
    * 'EditTags' view should have nested 'form' view with 'tags' table widget
    * Suggest using class cfme.common.TagPageView as view for 'EditTags' nav

    This class provides functionality to assign and unassigned tags for page models with
    standardized widgetastic views
    """

    def add_tag(self, category=None, tag=None, cancel=False, reset=False, details=True):
        """ Add tag to tested item

        Args:
            category: category(str)
            tag: tag(str) or Tag object
            cancel: set True to cancel tag assigment
            reset: set True to reset already set up tag
            details (bool): set False if tag should be added for list selection,
                            default is details page
        """
        if details:
            view = navigate_to(self, 'EditTagsFromDetails')
        else:
            view = navigate_to(self, 'EditTags')
        if isinstance(tag, Tag):
            category = tag.category.display_name
            tag = tag.display_name
        # Handle nested view.form and where the view contains form widgets
        try:
            updated = view.form.fill({
                "tag_category": '{} *'.format(category),
                "tag_name": tag
            })
        except NoSuchElementException:
            updated = view.form.fill({
                "tag_category": category,
                "tag_name": tag
            })
        # In case if field is not updated cancel the edition
        if not updated:
            cancel = True
        self._tags_action(view, cancel, reset)

    def add_tags(self, tags):
        """Add multiple tags

        Args:
            tags: pass dict with category name as key, and tag as value,
                 or pass list with tag objects
        """
        if isinstance(tags, dict):
            for category, tag in tags.items():
                self.add_tag(category=category, tag=tag)
        elif isinstance(tags, (list, tuple)):
            for tag in tags:
                self.add_tag(tag=tag)

    def remove_tag(self, category=None, tag=None, cancel=False, reset=False, details=True):
        """ Remove tag of tested item

        Args:
            category: category(str)
            tag: tag(str) or Tag object
            cancel: set True to cancel tag deletion
            reset: set True to reset tag changes
            details (bool): set False if tag should be added for list selection,
                            default is details page
        """
        if details:
            view = navigate_to(self, 'EditTagsFromDetails')
        else:
            view = navigate_to(self, 'EditTags')
        if isinstance(tag, Tag):
            category = tag.category.display_name
            tag = tag.display_name
        try:
            row = view.form.tags.row(category="{} *".format(category), assigned_value=tag)
        except RowNotFound:
            row = view.form.tags.row(category=category, assigned_value=tag)
        row[0].click()
        self._tags_action(view, cancel, reset)

    def remove_tags(self, tags):
        """Remove multiple of tags

        Args:
            tags: pass dict with category name as key, and tag as value,
                 or pass list with tag objects
        """
        if isinstance(tags, dict):
            for category, tag in tags.items():
                self.remove_tag(category=category, tag=tag)
        elif isinstance(tags, (list, tuple)):
            for tag in tags:
                self.remove_tag(tag=tag)

    def get_tags(self, tenant="My Company Tags"):
        """ Get list of tags assigned to item.

        Details entities should have smart_management widget
        For vm, providers, and other like pages 'SummaryTable' widget should be used,
        for user, group like pages(no tables on details page) use 'SummaryForm'

        Args:
            tenant: string, tags tenant, default is "My Company Tags"

        Returns: :py:class:`list` List of Tag objects
        """
        view = navigate_to(self, 'Details')
        tags = []
        tag_table = view.entities.smart_management
        tags_text = tag_table.get_text_of(tenant)
        if tags_text != 'No {} have been assigned'.format(tenant):
            for tag in list(tags_text):
                tag_category, tag_name = tag.split(':')
                tags.append(Tag(category=Category(display_name=tag_category),
                                display_name=tag_name.strip()))
        return tags

    def _tags_action(self, view, cancel, reset):
        """ Actions on edit tags page

        Args:
            view: View to use these actions(tag view)
            cancel: Set True to cancel all changes, will redirect to details page
            reset: Set True to reset all changes, edit tag page should be opened
        """
        if reset:
            view.form.reset.click()
            view.flash.assert_message('All changes have been reset')
        if cancel:
            view.form.cancel.click()
            view.flash.assert_success_message('Tag Edit was cancelled by the user')
        if not reset and not cancel:
            view.form.save.click()
            view.flash.assert_success_message('Tag edits were successfully saved')


@navigator.register(WidgetasticTaggable, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


@navigator.register(WidgetasticTaggable, 'EditTags')
class EditTagsFromListCollection(CFMENavigateStep):
    VIEW = TagPageView

    def prerequisite(self):
        if isinstance(self.obj, BaseCollection) or not isinstance(self.obj, BaseEntity):
            return navigate_to(self.obj, 'All')
        else:
            return navigate_to(self.obj.parent, 'All')

    def step(self, **kwargs):
        """
            kwargs: pass an entities objects or entities names
            Return: navigation step
        """
        if kwargs:
            for _, entity in kwargs.items():
                name = entity.name if isinstance(entity, BaseEntity) else entity
                self.prerequisite_view.entities.get_entity(
                    surf_pages=True, name=name).check()
        else:
            self.prerequisite_view.entities.get_entity(surf_pages=True, name=self.obj.name).check()
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')


class Validatable(object):
    """Mixin for various validations. Requires the class to be also :py:class:`Taggable`.

    :var :py:attr:`property_tuples`: Tuples which first value is the provider class's attribute
        name, the second value is provider's UI summary page field key. Should have values in
        child classes.
    """
    property_tuples = []

    def validate_properties(self):
        """Validation method which checks whether class attributes, which were used during creation
        of provider, are correctly displayed in Properties section of provider UI.

        The maps between class attribute and UI property is done via 'property_tuples' variable.

        Fails if some property does not match.
        """
        self.load_details(refresh=False)
        for property_tuple in self.property_tuples:
            expected_value = str(getattr(self, property_tuple[0], ''))
            shown_value = self.get_detail("Properties", property_tuple[1])
            assert expected_value == shown_value,\
                ("Property '{}' has wrong value, expected '{}' but was '{}'"
                 .format(property_tuple, expected_value, shown_value))

    def validate_tags(self, reference_tags):
        """Validation method which check tagging between UI and provided reference_tags.

        To use this method, `self`/`caller` should be extended with `Taggable` class

        Args:
            reference_tags: If you want to compare user input with UI, pass user input
                as `reference_tags`
        """
        if reference_tags and not isinstance(reference_tags, list):
            raise KeyError("'reference_tags' should be an instance of list")
        tags = self.get_tags()
        # Verify tags
        assert len(tags) == len(reference_tags), \
            ("Tags count between Provided and UI mismatch, expected '{}' but was '{}'"
             .format(reference_tags, tags))
        for ref_tag in reference_tags:
            found = False
            for tag in tags:
                if ref_tag.category.display_name == tag.category.display_name \
                        and ref_tag.display_name == tag.display_name:
                    found = True
            assert found, ("Tag '{}' not found in UI".format(ref_tag))


class TopologyMixin(object):
    """Use this mixin to have simple access to the Topology page.
    To use this `TopologyMixin` you have to implement `load_topology_page`
    function, which should take to topology page

    Sample usage:

    .. code-block:: python

        # You can retrieve the elements details as it is in the UI
        topology.elements  # => 'hostname'
        # You can do actions on topology page
        topology.display_names.enable()
        topology.display_names.disable()
        topology.display_names.is_enabled
        # You can do actions on topology search box
        topology.search_box.text(text='hello')
        topology.search_box.text(text='hello', submit=False)
        topology.search_box.submit()
        topology.search_box.clear()
        # You can get legends and can perform actions
        topology.legends
        topology.pod.name
        topology.pod.is_active
        topology.pod.set_active()
        # You can get elements, element parents and children
        topology.elements
        topology.elements[0].parents
        topology.elements[0].children
        topology.elements[0].double_click()
        topology.elements[0].is_displayed()

    """
    # @cached_property
    # def topology(self):
    #     return Topology(self)


class UtilizationMixin(object):
    """Use this mixin to have simple access to the Utilization information of an object.

    Requires that the class(page) has ``load_details(refresh)`` method
    and ``taggable_type`` should be defined.

    All the chart names from the UI are "attributized".

    Sample usage:
    .. code-block:: python

        # You can list available charts
        page.utilization.charts  # => '[ 'jvm_heap_usage_bytes','web_sessions','transactions']'
        # You can get the data from chart
        page.utilization.jvm_heap_usage_bytes.list_data_chart()  # => returns data as list
        # You can get the data from table
        provider.utilization.jvm_heap_usage_bytes.list_data_table()  # => returns data as list
        # You can get the data from wrapanapi
        page.utilization.jvm_heap_usage_bytes.list_data_mgmt()  # => returns data as list
        # You can change chart option
        page.utilization.jvm_non_heap_usage_bytes.option.set_by_visible_text(op_interval='Daily')
        # You can list available ledgends
        page.utilization.jvm_non_heap_usage_bytes.legends
        # You can enable/disable legends
        page.utilization.jvm_non_heap_usage_bytes.committed.set_active(active=False) # => Disables
        page.utilization.jvm_non_heap_usage_bytes.committed.set_active(active=True) # => Enables
    """
    # @cached_property
    # def utilization(self):
    #     return Utilization(self)
