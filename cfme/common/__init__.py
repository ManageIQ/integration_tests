# -*- coding: utf-8 -*-
import re
from functools import partial
from navmazing import NavigateToSibling
from urlparse import urlparse
from widgetastic.exceptions import NoSuchElementException, RowNotFound
from widgetastic_patternfly import BootstrapSelect, Button, Input
from widgetastic.widget import Table, Text, View
from widgetastic_manageiq import BaseNonInteractiveEntitiesView, Calendar
from widgetastic.utils import VersionPick, Version

from cached_property import cached_property
from cfme.base.login import BaseLoggedInPage
from cfme.configure.configuration.region_settings import Category, Tag
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import BootstrapTreeview, flash, form_buttons, toolbar
from cfme.web_ui.timelines import Timelines
from cfme.web_ui.topology import Topology
from cfme.web_ui.utilization import Utilization
from cfme.utils.appliance.implementations.ui import navigate_to, navigator, CFMENavigateStep
from cfme.utils import attributize_string
from cfme.utils.log import logger
from cfme.utils.pretty import Pretty
from cfme.utils.units import Unit
from cfme.utils.wait import wait_for, TimedOutError

pol_btn = partial(toolbar.select, "Policy")


class PolicyProfileAssignable(object):
    """This class can be inherited by anything that provider load_details method.

    It provides functionality to assign and unassign Policy Profiles
    """
    manage_policies_tree = BootstrapTreeview("protectbox")

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
        self.load_details(refresh=True)
        pol_btn("Manage Policies")
        for policy_profile in policy_profile_names:
            if assign:
                self.manage_policies_tree.check_node(policy_profile)
            else:
                self.manage_policies_tree.uncheck_node(policy_profile)
        form_buttons.save()
        flash.assert_no_errors()


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


class SummaryMixin(object):
    """Use this mixin to have simple access to the Summary informations of an object.

    Requires that the class has ``load_details(refresh)`` method defined.

    All the names from the UI are "attributized".

    Sample usage:

    .. code-block:: python

        # You can retrieve the text value as it is in the UI
        provider.summary.properties.host_name.text_value  # => 'hostname'
        # Or let it guess if it is a number and return float or int
        provider.summary.properties.aggregate_host_cpus.value  # => 12
        # You can get the image address
        provider.summary.foo.bar.img  # => value parsed by urlparse()
        # Or the onclick link
        provider.summary.foo.bar.link  # => 'http://foo/bar'
        # Check if it is clickable
        assert provider.summary.xyz.qwer.clickable

        # You can iterate like it was a dictionary
        for table_name, table in provider.summary:
            # table_name contains title of the table
            for key, value in table:
                # key contains the left cell text, value contains the value holder
                print('{}: {}'.format(key, value.text_value))


    """
    @cached_property
    def summary(self):
        return Summary(self)


class Summary(object):
    """Summary container class. An entry point to the summary listing"""
    HEADERS = '//th[@align="left"]'

    def __init__(self, o):
        self._object = o
        self._keys = []
        self.reload()

    def __repr__(self):
        return "<Summary {}>".format(" ".join(self._keys))

    def reload(self):
        for key in self._keys:
            try:
                delattr(self, key)
            except AttributeError:
                pass
        self._keys = []
        self._object.load_details(refresh=True)
        for header in sel.elements(self.HEADERS):
            header_text = sel.text_sane(header)
            header_id = attributize_string(header_text)
            table_object = SummaryTable(self._object, header_text, header)
            setattr(self, header_id, table_object)
            self._keys.append(header_id)

    def __iter__(self):
        """This enables you to iterate through like it was a dictionary, just without .iteritems"""
        for key in self._keys:
            yield (key, getattr(self, key))

    def groups(self):
        """Returns a dictionary of keys (table titles) and table objects."""
        return dict(iter(self))

    @property
    def group_names(self):
        """Returns names of the tables."""
        return self._keys


class SummaryTable(object):
    ROWS = '../../../tbody/tr'

    MULTIKEY_LOC = '../../../tbody/tr[1]/td/strong'

    def __init__(self, o, text, entry, skip_load=False):
        self._object = o
        self._text = text
        self._entry = entry
        self._raw_keys = []
        self._keys = []
        self._multitable = False
        if not skip_load:
            self.load()
        else:
            logger.warning(
                "Child SummaryTable created for {table_name}, "
                "this table wasn't initialized due to skip_load value".format(
                    table_name=self._text))

    def __repr__(self):
        if self._multitable:
            return "<SummaryTable {main_table_name}:\n\t {sub_tables}>".format(
                main_table_name=self._text,
                sub_tables='\n\t'.join([repr(getattr(self, key)) for key in self._keys]))

        return "<SummaryTable {} {}>".format(
            repr(self._text),
            " ".join("{}={}".format(key, repr(getattr(self, key))) for key in self._keys))

    def load(self):
        self._raw_keys = []
        self._keys = []
        key_values = []
        if sel.is_displayed(self.MULTIKEY_LOC, root=self._entry):
            logger.warning(
                "Parent SummaryTable created for {table_name}, "
                "it might create few un-initialized SummaryTable".format(
                    table_name=self._text))
            self._multitable = True
            # get all table rows (include titles)
            table_rows = sel.elements(self.ROWS, root=self._entry)

            # parsing table titles
            table_titles = sel.elements('./td', root=table_rows[0])
            table_titles_text = [el.text.replace(" ", "_") for el in table_titles]

            # match each line values with the relevant title
            for row in table_rows[1:]:
                # creating mapping between title and row values
                row_mapping = dict(zip(table_titles_text,
                                       [el.text for el in sel.elements('./td', root=row)]))

                # set the value of the "name" column to be the key of the entire table,
                # if "name" is not available setting the most left element to be the key
                row_key = row_mapping.get("Name", row_mapping.keys()[0])

                # creating empty table to populate the row data as regular table
                table = SummaryTable(self._object,
                                     row_key,
                                     row, skip_load=True)
                # set the keys of the table to table object
                table._keys = row_mapping.keys()

                # add attr for each key
                for key in row_mapping.keys():
                    setattr(table, key, row_mapping[key])

                # add the entire table to parent table keys
                self._keys.append(row_key)

                # add attr to parent table
                setattr(self, row_key, table)
            return

        for row in sel.elements(self.ROWS, root=self._entry):
            tds = sel.elements('./td', root=row)
            key = tds[0]
            klass = sel.get_attribute(key, 'class')
            if klass and 'label' in klass:
                # Ordinary field
                key_id = attributize_string(sel.text_sane(key))
                value = tuple(tds[1:])
                try:
                    rowspan = int(sel.get_attribute(key, 'rowspan'))
                except (ValueError, TypeError):
                    rowspan = None
                if rowspan:
                    key_values.append((key, key_id, [value]))
                else:
                    key_values.append((key, key_id, value))
            else:
                # value of last key_values should be extended
                key_values[-1][2].append(tuple(tds))
        for key, key_id, value in key_values:
            value_object = process_field(value)
            setattr(self, key_id, value_object)
            self._raw_keys.append(sel.text_sane(key))
            self._keys.append(key_id)

    def reload(self):
        self._object.load_details(refresh=True)
        for key in self._keys:
            try:
                delattr(self, key)
            except AttributeError:
                pass
        return self.load()

    @property
    def raw_keys(self):
        return self._raw_keys

    @property
    def keys(self):
        return self._keys

    def __iter__(self):
        for key in self._keys:
            yield (key, getattr(self, key))

    def items(self):
        return dict(iter(self))


class SummaryValue(object):
    def __init__(self, el):
        self._el = el

    def __repr__(self):
        return repr(self.text_value)

    @cached_property
    def img(self):
        try:
            img_o = sel.element('./img', root=self._el)
            return urlparse(sel.get_attribute(img_o, 'src').strip())
        except sel.NoSuchElementException:
            return None

    @cached_property
    def text_value(self):
        return sel.text_sane(self._el)

    @cached_property
    def value(self):
        # Try parsing a number
        try:
            return int(self.text_value)
        except (ValueError, TypeError):
            try:
                return float(self.text_value)
            except (ValueError, TypeError):
                try:
                    return Unit.parse(self.text_value)
                except ValueError:
                    return self.text_value

    @cached_property
    def link(self):
        if sel.get_attribute(sel.element('..', root=self._el), 'onclick'):
            return self._el
        else:
            return None

    @property
    def clickable(self):
        return self.link is not None

    def click(self):
        """A convenience function to click the summary item."""
        return sel.click(self)

    def _custom_click_handler(self, wait_ajax):
        if not self.clickable:
            raise ValueError("Cannot click on {} because it is not clickable".format(repr(self)))
        try:
            return sel.click(self.link, wait_ajax, no_custom_handler=True)
        except sel.StaleElementReferenceException:
            raise RuntimeError('Couldnt click on {} because the page was left.'.format(repr(self)))


def process_field(values):
    if isinstance(values, list):
        return map(process_field, values)
    else:
        if len(values) == 1:
            return SummaryValue(values[0])
        else:
            return map(SummaryValue, values)


class Validatable(SummaryMixin):
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
    @cached_property
    def topology(self):
        return Topology(self)


class TimelinesMixin(object):
    """Use this mixin to have simple access to the Timelines page.
    To use this `TimelinesMixin` you have to implement `load_timelines_page`
    function, which should take to timelines page

    Sample usage:

    .. code-block:: python

        # Change Timelines showing interval Select
        timelines.change_interval('Hourly')
        # Change Timelines showing event group Select
        timelines.select_event_category('Application')
        # Change Level of showed Timelines
        timelines.change_level('Detail')
        # Check whether timelines contain particular event
        # which is generated after provided datetime
        timelines.contains_event('hawkular_deployment.ok', before_test_date)

    """
    @cached_property
    def timelines(self):
        return Timelines(self)


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
    @cached_property
    def utilization(self):
        return Utilization(self)


class ExpressionEditor(View, Pretty):
    """This class enables to embed the expression in a Form.

    Args:
        show_func: Function to call to show the expression if there are more of them.
    """

    @View.nested
    class field_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        field = BootstrapSelect("chosen_field")
        key = BootstrapSelect("chosen_key")
        value = Input(name="chosen_value")
        user_input = Input(name="user_input")

    @View.nested
    class field_date_form(View):  # noqa
        dropdown_select = BootstrapSelect("chosen_from_1")
        input_select_date = Calendar(name="miq_date_1_0")
        input_select_time = BootstrapSelect("miq_time_1_0")

    @View.nested
    class count_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        count = BootstrapSelect("chosen_count")
        key = BootstrapSelect("chosen_key")
        value = Input(name="chosen_value")
        user_input = Input(name="user_input")

    @View.nested
    class tag_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        tag = BootstrapSelect("chosen_tag")
        value = BootstrapSelect("chosen_value")
        user_input = Input(name="user_input")

    @View.nested
    class find_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        field = BootstrapSelect("chosen_field")
        skey = BootstrapSelect("chosen_skey")
        value = Input(name="chosen_value")
        check = BootstrapSelect("chosen_check")
        cfield = BootstrapSelect("chosen_cfield")
        ckey = BootstrapSelect("chosen_ckey")
        cvalue = Input(name="chosen_cvalue")

    @View.nested
    class registry_form_view(View):  # noqa
        type = BootstrapSelect("chosen_typ")
        key = Input(name="chosen_regkey")
        value = Input(name="chosen_regval")
        operation = BootstrapSelect("chosen_key")
        contents = Input(name="chosen_value")

    @View.nested
    class date_specific_form_view(View):  # noqa
        date = Calendar(name="miq_date_1_0")
        time = BootstrapSelect("miq_time_1_0")

    @View.nested
    class date_relative_form_view(View):  # noqa
        from_ = BootstrapSelect("chosen_from_1")
        through = BootstrapSelect("chosen_through_1")

    ROOT = "//div[@id='exp_editor_div']"
    MAKE_BUTTON = "//span[not(contains(@style,'none'))]//img[@alt='{}']"
    ATOM_ROOT = "./div[@id='exp_atom_editor_div']"
    EXPRESSIONS_ROOT = "./fieldset/div"
    COMMIT = Button(title="Commit expression element changes")
    DISCARD = Button(title="Discard expression element changes")
    REMOVE = VersionPick({
        Version.lowest(): ("//span[not(contains(@style, 'none'))]/"
            "/img[@alt='Remove this expression element']"),
        "5.8": Button(title="Remove this expression element"),
    })
    NOT = VersionPick({
        Version.lowest(): ("//span[not(contains(@style, 'none'))]"
           "//img[@alt='Wrap this expression element with a NOT']"),
        "5.8": Button(title="Wrap this expression element with a NOT"),
    })
    OR = VersionPick({
        Version.lowest(): ("//span[not(contains(@style, 'none'))]/"
            "/img[@alt='OR with a new expression element']"),
        "5.8": Button(title="OR with a new expression element"),
    })
    AND = VersionPick({
        Version.lowest(): ("//span[not(contains(@style, 'none'))]/"
            "/img[@alt='AND with a new expression element']"),
        "5.8": Button(title="AND with a new expression element"),
    })
    REDO = VersionPick({
        Version.lowest(): "//img[@alt='Redo']",
        "5.8": Button(title="Redo the last change"),
    })
    UNDO = VersionPick({
        Version.lowest(): "//img[@alt='Undo']",
        "5.8": Button(title="Undo the last change"),
    })
    SELECT_SPECIFIC = "//img[@alt='Click to change to a specific Date/Time format']"
    SELECT_RELATIVE = "//img[@alt='Click to change to a relative Date/Time format']"

    pretty_attrs = ['show_loc']

    def __init__(self, parent, show_loc=None, logger=None):
        View.__init__(self, parent, logger=logger)
        self.show_loc = show_loc

    def __locator__(self):
        return self.ROOT

    def click_undo(self):
        self.browser.click(self.UNDO)

    def click_redo(self):
        self.browser.click(self.REDO)

    def click_and(self):
        self.browser.click(self.AND)

    def click_or(self):
        self.browser.click(self.OR)

    def click_not(self):
        self.browser.click(self.NOT)

    def click_remove(self):
        self.browser.click(self.REMOVE)

    def click_commit(self):
        self.browser.click(self.COMMIT)

    def click_discard(self):
        self.browser.click(self.DISCARD)

    def click_switch_to_relative(self):
        self.browser.click(self.SELECT_RELATIVE)

    def click_switch_to_specific(self):
        self.browser.click(self.SELECT_SPECIFIC)

    @property
    def _atom_root(self):
        return self.browser.element(self.ATOM_ROOT)

    @property
    def _expressions_root(self):
        return self.browser.element(self.EXPRESSIONS_ROOT)

    def select_first_expression(self):
        """There is always at least one (???), so no checking of bounds."""
        self.browser.elements("//a[contains(@id,'exp_')]", parent=self._expressions_root)[0].click()

    def select_expression_by_text(self, text):
        self.browser.click(
            "//a[contains(@id,'exp_')][contains(normalize-space(text()),'{}')]".format(text)
        )

    def no_expression_present(self):
        els = self.browser.elements("//a[contains(@id,'exp_')]", parent=self._expressions_root)
        if len(els) > 1:
            return False
        return els[0].text.strip() == "???"

    def any_expression_present(self):
        return not self.no_expression_present()

    def is_editing(self):
        try:
            self.browser.element(
                "//a[contains(@id,'exp_')][contains(normalize-space(text()),'???')]",
                parent=self._expressions_root
            )
            return True
        except NoSuchElementException:
            return False

    def delete_whole_expression(self):
        while self.any_expression_present():
            self.select_first_expression()
            self.click_remove()

    def read(self):
        """Returns whole expression as represented visually."""
        return self._expressions_root.text.encode("utf-8").strip()

    def enable_editor(self):
        try:
            el = self.browser.element(self.show_loc)
            wait_for(lambda: el.is_displayed, num_sec=2, delay=0.2)
            el.click()
        except (TimedOutError, NoSuchElementException):
            pass

    def fill(self, expression):
        if self.show_loc is not None:
            self.enable_editor()
        prog = self._create_program(expression, self)
        before = self._expressions_root.text.encode("utf-8").strip()
        prog()
        after = self._expressions_root.text.encode("utf-8").strip()
        return before != after

    def fill_count(self, count=None, key=None, value=None):
        """ Fills the 'Count of' type of form.

        If the value is unspecified and we are in the advanced search form (user input),
        the user_input checkbox will be checked if the value is None.

        Args:
            count: Name of the field to compare (Host.VMs, ...).
            key: Operation to do (=, <, >=, ...).
            value: Value to check against.
        Returns: See :py:func:`cfme.web_ui.fill`.
        """
        view = self.count_form_view
        view.fill(dict(type="Count of", count=count, key=key, value=value))
        # In case of advanced search box
        if view.user_input.is_displayed:
            user_input = value is None
            view.user_input.fill(user_input)
        self.click_commit()

    def fill_tag(self, tag=None, value=None):
        """ Fills the 'Tag' type of form.

        Args:
            tag: Name of the field to compare.
            value: Value to check against.
        """
        view = self.tag_form_view
        view.fill(dict(
            type="Tag",
            tag=tag,
            value=value
        ))
        # In case of advanced search box
        if view.user_input.is_displayed:
            user_input = value is None
            view.user_input.fill(user_input)
        self.click_commit()

    def fill_registry(self, key=None, value=None, operation=None, contents=None):
        """ Fills the 'Registry' type of form."""
        view = self.registry_form_view
        view.fill(dict(
            type="Registry",
            key=key,
            value=value,
            operation=operation,
            contents=contents,
        ))
        self.click_commit()

    def fill_find(self, field=None, skey=None, value=None, check=None, cfield=None, ckey=None,
                  cvalue=None):
        view = self.find_form_view
        view.fill(dict(
            type="Find",
            field=field,
            skey=skey,
            value=value,
            check=check,
            cfield=cfield,
            ckey=ckey,
            cvalue=cvalue
        ))
        self.click_commit()

    def fill_field(self, field=None, key=None, value=None):
        """ Fills the 'Field' type of form.

        Args:
            tag: Name of the field to compare (Host.VMs, ...).
            key: Operation to do (=, <, >=, IS NULL, ...).
            value: Value to check against.
        Returns: See :py:func:`cfme.web_ui.fill`.
        """
        field_norm = field.strip().lower()
        if ("date updated" in field_norm or "date created" in field_norm or
                "boot time" in field_norm or "timestamp" in field_norm):
            no_date = False
        else:
            no_date = True
        view = self.field_form_view
        view.fill(dict(
            type="Field",
            field=field,
            key=key,
            value=value if no_date else None,
        ))
        # In case of advanced search box
        if view.user_input.is_displayed:
            user_input = value is None
            view.user_input.fill(user_input)
        if not no_date:
            # Flip the right part of form
            view = self.field_date_form
            if (isinstance(value, basestring) and
                    not re.match(r"^[0-9]{2}/[0-9]{2}/[0-9]{4}$", value)):
                if not view.dropdown_select.is_displayed:
                    self.click_switch_to_relative()
                view.fill({"dropdown_select": value})
                self.click_commit()
            else:
                # Specific selection
                if not view.input_select_date.is_displayed:
                    self.click_switch_to_specific()
                if (isinstance(value, tuple) or isinstance(value, list)) and len(value) == 2:
                    date, time = value
                elif isinstance(value, basestring):  # is in correct format mm/dd/yyyy
                    # Date only (for now)
                    date = value[:]
                    time = None
                else:
                    raise TypeError("fill_field expects a 2-tuple (date, time) or string with date")
                # TODO datetime.datetime support
                view.input_select_date.fill(date)
                # Try waiting a little bit for time field
                # If we don't wait, committing the expression will glitch
                try:
                    wait_for(lambda: view.input_select_time.is_displayed, num_sec=6)
                    # It appeared, so if the time is to be set, we will set it
                    # (passing None glitches)
                    if time:
                        view.input_select_time.fill(time)
                except TimedOutError:
                    # Did not appear, ignore that
                    pass
                finally:
                    # And finally, commit the expression :)
                    self.click_commit()
        else:
            self.click_commit()

    def _run_commands(self, command_list, clear_expression=True, context=None):
        """ Run commands from the command list.

        Command list syntax:
            .. code-block:: python

                [
                    "function1",                                                # no args
                    "function2",                                                # dtto
                    {"fill_fields": {"field1": "value", "field2": "value"}},    # Passes kwargs
                    {"do_other_things": [1,2,3]}                                # Passes args
                ]

        In YAML:
            .. code-block:: yaml

                - function1
                - function2
                -
                    fill_fields:
                        field1: value
                        field2: value
                -
                    do_other_things:
                        - 1
                        - 2
                        - 3

        Args:
            command_list: :py:class:`list` object of the commands
            clear_expression: Whether to clear the expression before entering new one
            (default `True`)
            context: widget object
        """
        assert isinstance(command_list, list) or isinstance(command_list, tuple)
        step_list = []
        for command in command_list:
            if isinstance(command, basestring):
                # Single command, no params
                step_list.append(self._get_func(command, context))
            elif isinstance(command, dict):
                for key, value in command.iteritems():
                    func = self._get_func(key, context)
                    args = []
                    kwargs = {}
                    if isinstance(value, list) or isinstance(value, tuple):
                        args.extend(value)
                    elif isinstance(value, dict):
                        kwargs.update(value)
                    else:
                        raise Exception("I use '{}' type here!".format(type(value).__name__))
                    step_list.append(partial(func, *args, **kwargs))
            else:
                raise Exception("I cannot process '{}' type here!".format(type(command).__name__))
        if clear_expression:
            context.delete_whole_expression()
        for step in step_list:
            step()

    def _create_program(self, dsl_program, widget_object):
        """ Simple DSL to fill the expression editor.

        Syntax:
            DSL consists from statements. Statements are separated with newline or ;.
            Each statement is a single function call. Functions are called in this module.
            Function without parameters can be called like this:
            function
            or
            function()

            If the function has some parameters, you have to choose whether they are kwargs or args.
            DSL has no string literals, so if you want to call a function with classic parameters:
            function(parameter one, parameter two, you cannot use comma)
            And with kwargs:
            function(username=John Doe, password=top secret)
            You cannot split the statement to multiple lines as the DSL is regexp-based.

        Args:
            dsl_program: Source string with the program.
        Returns: Callable, which fills the expression.
        """
        SIMPLE_CALL = r"^[a-z_A-Z][a-z_A-Z0-9]*$"  # noqa
        ARGS_CALL = r"^(?P<name>[a-z_A-Z][a-z_A-Z0-9]*)\((?P<args>.*)\)$"  # noqa
        KWARG = r"^[^=]+=.*$"  # noqa
        command_list = []
        for i, line in enumerate([x.strip() for x in re.split(r"\n|;", dsl_program)]):
            if len(line) == 0:
                continue
            elif re.match(SIMPLE_CALL, line):
                command_list.append(line)
                continue
            args_match = re.match(ARGS_CALL, line)
            if not args_match:
                raise SyntaxError("Could not resolve statement `{}' on line {}".format(line, i))
            fname = args_match.groupdict()["name"]
            args = [x.strip() for x in args_match.groupdict()["args"].split(",")]
            if len(args) > 0 and len(args[0]) > 0:
                if re.match(KWARG, args[0]):
                    # kwargs
                    kwargs = dict([map(lambda x: x.strip(), x.split("=", 1)) for x in args])
                    command_list.append({fname: kwargs})
                else:
                    # Args
                    command_list.append({fname: [None if arg == "/None/" else arg for arg in args]})
            else:
                command_list.append(fname)
        return self._create_program_from_list(command_list, widget_object)

    def _create_program_from_list(self, command_list, widget_object):
        """ Create function which fills the expression from the command list.

        Args:
            command_list: Command list for :py:func:`run_program`
        Returns: Callable, which fills the expression.
        """
        return partial(self._run_commands, command_list, context=widget_object)

