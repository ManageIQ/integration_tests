# -*- coding: utf-8 -*-
import six
import random
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException, RowNotFound
from widgetastic_patternfly import (
    BootstrapSelect,
    Button,
    CheckableBootstrapTreeview,
    DropdownItemNotFound,
    SelectItemNotFound
)
from widgetastic.widget import Table, Text, View

from cfme.base.login import BaseLoggedInPage
from cfme.modeling.base import BaseCollection, BaseEntity
from cfme.configure.configuration.region_settings import Category, Tag
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils.log import logger
from cfme.utils.wait import wait_for
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
        policy_changed = False
        for policy_profile in policy_profile_names:
            if assign:
                policy_changed = view.policy_profiles.fill(
                    view.policy_profiles.CheckNode([policy_profile])
                ) or policy_changed
            else:
                policy_changed = view.policy_profiles.fill(
                    view.policy_profiles.UncheckNode([policy_profile])
                ) or policy_changed
        if policy_changed:
            view.save.click()
        else:
            view.cancel.click()
        details_view = self.create_view(navigator.get_class(self, 'Details').VIEW)
        details_view.flash.assert_no_error()

    def assign_policy_profiles_multiple_entities(self, entities, conditions, *policy_profile_names):
        """ Assign Policy Profiles to selected entity's on Collection All view

        Args:
            entities: list of entity's from collection table
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
            conditions: entities should match to

        Usage:

            .. code-block:: python

                collection = appliance.collections.container_images
                # assign OpenSCAP policy
                collection.assign_policy_profiles_multiple_entities(random_image_instances,
                                conditions=[{'name': 'dotnet/dotnet-20-rhel7'},
                                            {'name': 'dotnet/dotnet-20-runtime-rhel7'}],
                                'OpenSCAP profile')
        """
        map(self.assigned_policy_profiles.add, policy_profile_names)
        self._assign_or_unassign_policy_profiles_multiple_entities(
            entities, True, conditions, *policy_profile_names)

    def unassign_policy_profiles_multiple_entities(self, entities, conditions,
                                                   *policy_profile_names):
        """ UnAssign Policy Profiles to selected entity's on Collection All view

        Args:
            entities: list of entity's from collection table
            policy_profile_names: :py:class:`str` with Policy Profile names. After Control/Explorer
                coverage goes in, PolicyProfile objects will be also passable.
            conditions: entities should match to

        Usage:

            .. code-block:: python

                collection = appliance.collections.container_images
                # unassign OpenSCAP policy
                collection.unassign_policy_profiles_multiple_entities(random_image_instances,
                                conditions=[{'name': 'dotnet/dotnet-20-rhel7'},
                                            {'name': 'dotnet/dotnet-20-runtime-rhel7'}],
                                'OpenSCAP profile')
        """
        for pp_name in policy_profile_names:
            try:
                self.assigned_policy_profiles.remove(pp_name)
            except KeyError:
                pass
        self._assign_or_unassign_policy_profiles_multiple_entities(
            entities, False, conditions, *policy_profile_names)

    def _assign_or_unassign_policy_profiles_multiple_entities(
            self, entities, assign, conditions, *policy_profile_names):

        """DRY function for managing policy profiles.

        See :py:func:`assign_policy_profiles_multiple_entities`
         and :py:func:`unassign_policy_profiles_multiple_entities`

        Args:
            entities: list of entity's from collection table
            assign: Whether to assign or unassign.
            policy_profile_names: :py:class:`str` with Policy Profile names.
            conditions: entities should match to
        """
        view = navigate_to(self, 'All')

        # set item per page for maximum value in order to avoid paging,
        # that will cancel the already check entity's
        items_per_page = view.paginator.items_per_page
        view.paginator.set_items_per_page(1000)

        # check the entity's on collection ALL view
        view.entities.apply(func=lambda e: e.check(), conditions=conditions)

        wait_for(lambda: view.toolbar.policy.is_enabled, num_sec=5,
                 message='Policy drop down menu is disabled after checking some entities')
        view.toolbar.policy.item_select('Manage Policies')
        # get the object of the Manage Policies view
        manage_policies_view = self.create_view(navigator.get_class(self, 'ManagePolicies').VIEW)

        policy_changed = False
        for policy_profile in policy_profile_names:
            if assign:
                policy_changed = manage_policies_view.policy_profiles.fill(
                    manage_policies_view.policy_profiles.CheckNode([policy_profile])
                ) or policy_changed
            else:
                policy_changed = manage_policies_view.policy_profiles.fill(
                    manage_policies_view.policy_profiles.UncheckNode([policy_profile])
                ) or policy_changed
        if policy_changed:
            manage_policies_view.save.click()
        else:
            manage_policies_view.cancel.click()

        view.flash.assert_no_error()

        # return the previous number of items per page
        view.paginator.set_items_per_page(items_per_page)


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


class TaggableCommonBase(object):
    """Class represents common functionality for tagging via collection and entities pages"""

    def _set_random_tag(self, view):
        random_cat = random.choice(view.form.tag_category.all_options).text
        # '*' is added in UI almost to all categoly while tag selection,
        #  but doesn't need for Category object creation
        random_cat_cut = random_cat[:-1].strip() if random_cat[-1] == '*' else random_cat
        view.form.tag_category.fill(random_cat)
        # In order to get the right tags list we need to select category first to get loaded tags
        random_tag = random.choice([tag_option for tag_option in view.form.tag_name.all_options
                                    if "select" not in tag_option.text.lower()]).text
        tag = Tag(display_name=random_tag, category=Category(display_name=random_cat_cut))
        return tag

    def _assign_tag_action(self, view, tag):
        """Assign tag on tag page

        Args:
            view: View to use these actions(tag view)
            tag: Tag object
        Returns:
            True/False updated status
        """
        if not tag:
            tag = self._set_random_tag(view)
        category_name = tag.category.display_name
        tag_name = tag.display_name
        # Handle nested view.form and where the view contains form widgets
        try:
            updated = view.form.fill({
                "tag_category": '{} *'.format(category_name),
                "tag_name": tag_name
            })
        except (NoSuchElementException, SelectItemNotFound):
            updated = view.form.fill({
                "tag_category": category_name,
                "tag_name": tag_name
            })
        return tag, updated

    def _unassign_tag_action(self, view, tag):
        """Remove tag on tag page

        Args:
            view: View to use these actions(tag view)
            tag: Tag object
        """
        category = tag.category.display_name
        tag = tag.display_name
        try:
            row = view.form.tags.row(category="{} *".format(category), assigned_value=tag)
        except RowNotFound:
            row = view.form.tags.row(category=category, assigned_value=tag)
        row[0].click()

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


class Taggable(TaggableCommonBase):
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

    def add_tag(self, tag=None, cancel=False, reset=False, details=True):
        """ Add tag to tested item

        Args:
            tag: Tag object
            cancel: set True to cancel tag assigment
            reset: set True to reset already set up tag
            details (bool): set False if tag should be added for list selection,
                            default is details page
        """
        step = 'EditTagsFromDetails' if details else 'EditTags'
        view = navigate_to(self, step)
        added_tag, updated = self._assign_tag_action(view, tag)
        # In case if field is not updated cancel the edition
        if not updated:
            cancel = True
        self._tags_action(view, cancel, reset)
        return added_tag

    def add_tags(self, tags):
        """Add multiple tags

        Args:
            tags: list of tag objects
        """
        for tag in tags:
            self.add_tag(tag=tag)

    def remove_tag(self, tag, cancel=False, reset=False, details=True):
        """ Remove tag of tested item

        Args:
            tag: Tag object
            cancel: set True to cancel tag deletion
            reset: set True to reset tag changes
            details (bool): set False if tag should be added for list selection,
                            default is details page
        """
        step = 'EditTagsFromDetails' if details else 'EditTags'
        view = navigate_to(self, step)
        self._unassign_tag_action(view, tag)
        self._tags_action(view, cancel, reset)

    def remove_tags(self, tags):
        """Remove multiple of tags

        Args:
            tags: list of tag objects
        """
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
        entities = view.entities
        if hasattr(entities, 'smart_management'):
            tag_table = entities.smart_management
        else:
            tag_table = entities.summary('Smart Management')
        tags_text = tag_table.get_text_of(tenant)
        if tags_text != 'No {} have been assigned'.format(tenant):
            # check for users/groups page in case one tag string is returned
            for tag in [tags_text] if isinstance(tags_text, six.string_types) else list(tags_text):
                tag_category, tag_name = tag.split(':')
                tags.append(Tag(category=Category(display_name=tag_category),
                                display_name=tag_name.strip()))
        return tags


class TaggableCollection(TaggableCommonBase):

    def add_tag(self, item_objects, tag=None, cancel=False, reset=False):
        """ Add tag to tested item

        Args:
            item_objects: list of entity object, also can be passed lint on entities names
            tag: Tag object
            cancel: set True to cancel tag assigment
            reset: set True to reset already set up tag
        Returns:
            tag object
        """
        view = navigate_to(self, 'All')
        for item in item_objects:
            name = item if isinstance(item, six.string_types) else item.name
            view.entities.get_entity(surf_pages=True, name=name).check()
        view = self._open_edit_tag_page(view)
        added_tag, updated = self._assign_tag_action(view, tag)
        # In case if field is not updated cancel the edition
        if not updated:
            cancel = True
        self._tags_action(view, cancel, reset)
        return added_tag

    def add_tags(self, item_objects, tags):
        """Add multiple tags

        Args:
            item_objects: list of entity object, also can be passed lint on entities names
            tags: list of tag objects
        """
        for tag in tags:
            self.add_tag(item_objects, tag=tag)

    def remove_tag(self, item_objects, tag, cancel=False, reset=False):
        """ Remove tag of tested item

        Args:
            item_objects: list of entity object, also can be passed lint on entities names
            tag: Tag object
            cancel: set True to cancel tag deletion
            reset: set True to reset tag changes
        """
        view = navigate_to(self, 'All')
        for item in item_objects:
            name = item if isinstance(item, six.string_types) else item.name
            view.entities.get_entity(surf_pages=True, name=name).check()
        view = self._open_edit_tag_page(view)
        self._unassign_tag_action(view, tag)
        self._tags_action(view, cancel, reset)

    def remove_tags(self, item_objects, tags):
        """Remove multiple of tags

        Args:
            item_objects: list of entity object, also can be passed lint on entities names
            tags: list of tag objects
        """
        for tag in tags:
            self.remove_tag(item_objects, tag=tag)

    def _open_edit_tag_page(self, parent_view):
        try:
            parent_view.toolbar.policy.item_select('Edit Tags')
        except DropdownItemNotFound:
            parent_view.toolbar.policy.item_select(
                "Edit 'My Company' Tags for this {}".format(type(self.__name__)))
        return self.create_view(TagPageView)


@navigator.register(Taggable, 'EditTagsFromDetails')
class EditTagsFromDetails(CFMENavigateStep):
    VIEW = TagPageView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        # not for all entities we have select like 'Edit Tags',
        # users, groups, tenants have specific dropdown title
        try:
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
        except DropdownItemNotFound:
            self.prerequisite_view.toolbar.policy.item_select(
                "Edit 'My Company' Tags for this {}".format(type(self.obj).__name__))


@navigator.register(Taggable, 'EditTags')
class EditTagsFromListCollection(CFMENavigateStep):
    VIEW = TagPageView

    def prerequisite(self):
        if isinstance(self.obj, BaseCollection) or not isinstance(self.obj, BaseEntity):
            return navigate_to(self.obj, 'All')
        else:
            return navigate_to(self.obj.parent, 'All')

    def step(self, *args):
        """
            args: pass an entities objects or entities names
            Return: navigation step
        """
        if args:
            for entity in args:
                name = entity.name if isinstance(entity, BaseEntity) else entity
                self.prerequisite_view.entities.get_entity(
                    surf_pages=True, name=name).check()
        else:
            self.prerequisite_view.entities.get_entity(surf_pages=True, name=self.obj.name).check()
        # not for all entities we have select like 'Edit Tags',
        # users, groups, tenants have specific dropdown title
        try:
            self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
        except DropdownItemNotFound:
            self.prerequisite_view.toolbar.policy.item_select(
                "Edit 'My Company' Tags for this {}".format(type(self.obj).__name__))


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
