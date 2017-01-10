# -*- coding: utf-8 -*-
from navmazing import NavigateToSibling, NavigateToAttribute
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, navigate_to, CFMENavigateStep

from copy import copy
from functools import partial
from xml.sax.saxutils import quoteattr

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui import match_location, summary_title
import cfme.web_ui.flash as flash
import cfme.web_ui.toolbar as tb
from cfme.web_ui.tabstrip import select_tab
from cfme.web_ui import Form, Table, UpDownSelect, fill, Select, ScriptBox, DHTMLSelect,\
    Region, form_buttons, accordion, Input, AngularSelect
import cfme.exceptions as exceptions
from utils.update import Updateable
from utils import error, version, on_rtd
from collections import Mapping
import re
from utils.log import logger
from utils import classproperty, pretty

datastore_tree = partial(accordion.tree, "Datastore", "Datastore")
cfg_btn = partial(tb.select, 'Configuration')
match_page = partial(match_location, controller='miq_ae_class', title='Automate')


def table_click(name, type):
    try:
        sel.click(
            (
                '//tr[.//*[(self::span or self::i) and contains(@class, {})]]'
                '/td[not(contains(@class, "narrow")) and normalize-space(.)={}]'
            ).format(quoteattr(type), quoteattr(name)))
    except sel.NoSuchElementException:
        raise exceptions.CandidateNotFound({'type': type, 'name': name})


class TreeNode(pretty.Pretty):
    pretty_attrs = ['name']

    @property
    def name_in_tree(self):
        return self.name

    @property
    def name_in_table(self):
        return self.name

    @property
    def path(self):
        """Returns the path to this object as a list starting from the root"""
        # A node with no name is the root node
        if self.parent:
            return list(self.parent.path) + [self.name_in_tree]
        else:
            return [self.name_in_tree]

    def exists(self):
        try:
            navigate_to(self, 'Details')
        except exceptions.CandidateNotFound:
            return False
        else:
            return True

    @property
    def nav_path(self):
        return ["Datastore"] + self.path

    def navigate_tree(self):
        return accordion.tree('Datastore', *self.nav_path)

    def nav_edit(self):
        dp_length = 2
        if len(self.nav_path) > dp_length:
            cfg_btn('Edit Selected Item')
        else:
            cfg_btn('Edit Selected Namespace')


class CopiableTreeNode(TreeNode):
    copy_form = Form(fields=[
        ("domain", AngularSelect("domain")),
        ("domain_text_only", (
            "//label[contains(@class, 'control-label') and normalize-space(.)='To Domain']/"
            "../div/p")),
        ("override", Input("override_source"))
    ])

    copy_button = form_buttons.FormButton("Copy")

    @property
    def class_name(self):
        """Used for gathering the object name from the class name. If the name is not same,
        you can set it manually. This exploits the fact that the classes are named exactly as it
        appears in the UI, so it will work unless someone changes ui/class name. Then you can set it
        manually, as it contains setter."""
        try:
            return self._class_name
        except AttributeError:
            return type(self).__name__

    @class_name.setter
    def class_name(self, value):
        self._class_name = value

    def _open_copy_dialog(self):
        navigate_to(self, 'Details')
        cfg_btn("Copy this {}".format(self.class_name))

    # TODO: Make possible change `override` (did not do that because of pop-up tree)
    def copy_to(self, domain=None):
        self._open_copy_dialog()
        if isinstance(domain, Domain):
            domain_name = domain.name
        else:
            domain_name = str(domain)
        if sel.is_displayed(self.copy_form.domain):
            fill(self.copy_form, {"domain": domain_name, "override": True})
        else:
            # If there is only one domain, therefore the select is not present, only text
            domain_selected = sel.text(self.copy_form.domain_text_only).strip()
            if domain_selected != domain_name:
                raise ValueError(
                    "There is only one domain to select and that is {}".format(domain_selected))
            fill(self.copy_form, {"override": True})
        sel.click(self.copy_button)
        if version.current_version() < "5.7":
            flash.assert_message_match("Copy selected Automate {} was saved".
                format(self.class_name))

        # Bunch'o functions that copy the chain to the domain and change domain's name
        def _change_path_in_namespace(o, new_domain_name):
            if isinstance(o, Domain):
                if isinstance(new_domain_name, Domain):
                    return new_domain_name
                new_domain = copy(o)
                new_domain.name = new_domain_name
                return new_domain
            else:
                new_obj = copy(o)
                if new_obj.parent is None:
                    # This should happen in the domain part of this func so Error here
                    raise Exception(
                        "It is not expected that {} has no parent!".format(type(new_obj).__name__))
                new_obj.parent = _change_path_in_namespace(
                    new_obj.parent, new_domain_name)
                return new_obj

        def _change_parent_path_until_namespace(obj, new_domain_name):
            if isinstance(obj, Namespace):
                return _change_path_in_namespace(obj, new_domain_name)
            else:
                new_obj = copy(obj)
                if new_obj.parent is None:
                    # This should happen in the namespace func so Error here
                    raise Exception(
                        "It is not expected that {} has no parent!".format(type(new_obj).__name__))
                new_obj.parent = _change_parent_path_until_namespace(
                    new_obj.parent, new_domain_name)
                return new_obj

        return _change_parent_path_until_namespace(self, domain)


class Domain(Navigatable, TreeNode, Updateable):
    form = Form(fields=[('name', Input('ns_name')),
                        ('description', Input('ns_description')),
                        ('enabled', Input('ns_enabled'))])

    def __init__(self, name=None, description=None, enabled=False, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.parent = None
        self.description = description
        self.enabled = enabled

    def create(self, cancel=False, allow_duplicate=False):
        if self.exists() and not allow_duplicate:
            return
        navigate_to(self, 'Add')
        fill(self.form, {'name': self.name,
                         'description': self.description,
                         'enabled': self.enabled},
             action=form_buttons.cancel if cancel else form_buttons.add)

    def update(self, updates):
        navigate_to(self, 'Edit')
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        cfg_btn("Remove this Domain", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_message_match('Automate Domain "{}": Delete successful'.format(
            self.description or self.name))

    def _nav_orig(self):
        try:
            accordion.tree('Datastore', *self.nav_path)
            return True, None
        except exceptions.CandidateNotFound as e:
            return False, e

    def _nav_locked(self):
        path = self.nav_path
        path[-1] = path[-1] + " (Locked)"  # Try the Locked version
        try:
            accordion.tree('Datastore', *path)
            return True, None
        except exceptions.CandidateNotFound as e:
            return False, e

    def _nav_disabled(self):
        path = self.nav_path
        path[-1] = path[-1] + " (Disabled)"  # Try the Locked version
        try:
            accordion.tree('Datastore', *path)
            return True, None
        except exceptions.CandidateNotFound as e:
            return False, e

    def navigate_tree(self):
        last_nav, e = self._nav_orig()
        if last_nav is not True:
            nav = self._nav_locked()[0]
            if nav is not True:
                nav = self._nav_disabled()[0]
                if nav is not True:
                    raise e

    @property
    def is_locked(self):
        navigate_to(self, 'Details')
        return (not self._nav_orig()[0]) and self._nav_locked()[0]

    @property
    def is_enabled(self):
        navigate_to(self, 'Edit')
        self.enabled = sel.element(self.form.enabled).is_selected()
        return self.enabled

    @classproperty
    def default(cls):
        if on_rtd:
            return cls('Default')
        else:
            if not hasattr(cls, "_default_domain"):
                cls._default_domain = cls('Default')
            return cls._default_domain


@navigator.register(Domain, 'Add')
class DomainNew(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self):
        accordion.tree('Datastore', 'Datastore')
        cfg_btn('Add a New Domain')

    def am_i_here(self):
        return match_location(summary='Adding a new Automate Domain')


@navigator.register(Domain, 'Order')
class DomainOrder(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self):
        accordion.tree('Datastore', 'Datastore')
        cfg_btn('Edit Priority Order of Domains')

    def am_i_here(self):
        return match_location(summary='Datastore') and sel.is_displayed('#seq_fields')


@navigator.register(Domain, 'Details')
class DomainDetails(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'AutomateExplorer')

    def step(self):
        self.obj.navigate_tree()

    def am_i_here(self):
        return match_location(summary='Automate Domain "{}"'.format(self.obj.name))


@navigator.register(Domain, 'Edit')
class DomainEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Domain')

    def am_i_here(self):
        return match_location(summary='Editing Automate Domain "{}"'.format(self.obj.name))


domain_order_selector = UpDownSelect(
    "select#seq_fields",
    "//img[@alt='Move selected fields up']",
    "//img[@alt='Move selected fields down']")


def get_domain_order():
    navigate_to(Domain, 'Order')
    return domain_order_selector.get_items()


def set_domain_order(items):
    original_order = get_domain_order()
    # We pick only the same amount of items for comparing
    original_order = original_order[:len(items)]
    if items == original_order:
        return  # Ignore that, would cause error on Save click
    fill(domain_order_selector, items)
    sel.click(form_buttons.save)


class Namespace(Navigatable, TreeNode, Updateable):
    form = Form(fields=[('name', "//*[@id='ns_name']"),
                        ('description', "//*[@id='ns_description']")])

    @classmethod
    def make_path(cls, *names, **kwargs):
        """
        Make a set of nested Namespace objects with the given path.

        Usage:
            #eg.
                n = Namespace.make_path("foo", "bar")
            #is equivalent to:
                n = Namespace(name="bar", parent=Namespace(name="foo"))
        """
        domain = kwargs.get('domain', None)
        parent = kwargs.get('parent', None)
        create_on_init = kwargs.get('create_on_init', False)

        names = list(names)
        parent = domain or parent
        ns = cls(name=names.pop(0), parent=parent)
        if create_on_init and not ns.exists():
            ns.create()
        if names:
            return cls.make_path(*names, parent=ns, create_on_init=create_on_init)
        else:
            return ns

    def __init__(self, name=None, description=None, parent=None, domain=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.parent = parent or (domain if isinstance(domain, Domain) else Domain.default)

    def create(self, cancel=False, allow_duplicate=False):
        if self.parent is not None and not self.parent.exists():
            self.parent.create()
        if self.exists() and not allow_duplicate:
            return
        navigate_to(self, 'Add')
        form_data = {'name': self.name,
                     'description': self.description}
        try:
            fill(self.form, form_data, action=form_buttons.cancel if cancel else form_buttons.add)
            flash.assert_success_message('Automate Namespace "{}" was added'.format(self.name))
        finally:
            # if there was a validation error we need to cancel out
            if sel.is_displayed(form_buttons.cancel):
                sel.click(form_buttons.cancel)

    def update(self, updates, cancel=False):
        navigate_to(self, 'Edit')
        form_data = {'name': updates.get('name') or None,
                     'description': updates.get('description') or None}
        fill(self.form, form_data, action=form_buttons.cancel if cancel else form_buttons.save)
        flash.assert_success_message('Automate Namespace "{}" was saved'.format(
                                     updates.get('name', self.name)))

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        cfg_btn('Remove this Namespace', invokes_alert=True)
        sel.handle_alert(cancel)
        del_msg = 'Automate Namespace "{}": Delete successful'.format(self.description)
        flash.assert_success_message(del_msg)

    def __repr__(self):
        return "<{}.{} name={}, path={}>".format(__name__, type(self).__name__,
                                            self.name, self.path)


@navigator.register(Namespace, 'Add')
class NamespaceNew(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        cfg_btn('Add a New Namespace')

    def am_i_here(self):
        return match_location(summary='Adding a new Automate Namespace')


@navigator.register(Namespace, 'Details')
class NamespaceDetails(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        table_click(self.obj.name, 'ae_namespace')

    def am_i_here(self):
        return match_location(summary='Automate Namespace "{}"'.format(self.obj.name))


@navigator.register(Namespace, 'Edit')
class NamespaceEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Namespace')

    def am_i_here(self):
        return match_location(summary='Editing Automate Namespace "{}"'.format(self.obj.name))


class Class(Navigatable, CopiableTreeNode, Updateable):
    """Represents a Class in the CFME ui.

    Providing a setup_schema dict, creates the Class with teh specified schema

    """

    form = Form(fields=[('name_text', Input('name')),
                        ('display_name_text', Input('display_name')),
                        ('description_text', Input('description')),
                        ('inherits_from_select', Select("//select[@name='inherits_from']"))])

    def __init__(self, name=None, display_name=None, description=None, inherits_from=None,
                 namespace=None, setup_schema=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.display_name = display_name
        self.description = description
        self.inherits_from = inherits_from
        self.namespace = namespace
        self.setup_schema = setup_schema

    @property
    def parent(self):
        return self.namespace

    @parent.setter
    def parent(self, p):
        self.namespace = p

    @property
    def name_in_tree(self):
        """The item is displayed differently with display_name"""
        if self.display_name:
            return "{} ({})".format(self.display_name, self.name)
        else:
            return self.name

    @property
    def name_in_table(self):
        """The item is displayed differently with display_name"""
        if self.display_name:
            return self.display_name
        else:
            return self.name

    def path_str(self):
        """Returns string path to this class, eg ns1/ns2/ThisClass"""
        path = self.path
        path[-1] = self.name  # override the display_name madness
        path = "/".join(path)
        return "/" + path

    def create(self, cancel=False, allow_duplicate=False):
        if self.parent is not None and not self.parent.exists():
            self.parent.create()
        if self.exists() and not allow_duplicate:
            return
        navigate_to(self, 'Add')
        fill(self.form, {'name_text': self.name,
                         'description_text': self.description,
                         'display_name_text': self.display_name,
                         'inherits_from_select':
                         self.inherits_from and self.inherits_from.path_str()},
             action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_success_message('Automate Class "{}" was added'.format(self.path_str()))
        if self.setup_schema:
            self.edit_schema(add_fields=self.setup_schema)

    def update(self, updates, cancel=False):
        navigate_to(self, 'Edit')
        update_values = {
            'name_text': updates.get('name'),
            'description_text': updates.get('description'),
            'inherits_from_select':
            updates.get('inherits_from') and updates.get('inherits_from').path_str()}
        if "display_name" in updates:
            # We need to specifically override the display_name
            update_values["display_name_text"] = updates["display_name"] or ""  # None -> emptystr
        fill(
            self.form, update_values,
            action=form_buttons.cancel if cancel else form_buttons.save)

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        cfg_btn('Remove this Class', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()

    class SchemaField(Updateable):
        def __init__(self, name=None, type_=None, data_type=None, default_value=None,
                     display_name=None, description=None, sub=None, collect=None, message=None,
                     on_entry=None, on_exit=None, on_error=None, max_retries=None, max_time=None):
            self.name = name
            # As of CFME 5.7 type is required
            self.type_ = type_ or 'Assertion'
            self.data_type = data_type
            self.default_value = default_value
            self.display_name = display_name
            self.description = description
            self.sub = sub
            self.collect = collect
            self.message = message
            self.on_entry = on_entry
            self.on_exit = on_exit
            self.on_error = on_error
            self.max_retries = max_retries
            self.max_time = max_time

        def get_form(self, blank=False):
            """Gets a form for a field that already exists (by its name). Or if
               blank=True, get the form for a new field.  Must be on
               the correct page before calling this.
            """
            idx = ""
            if blank:
                row_id = ""  # for new entries, id attribute has no trailing '_x'
            else:
                idx = sel.get_attribute(
                    "//input[starts-with(@id, 'fields_name') and @value='{}']"
                    .format(self.name), 'id').split("_")[-1]
                row_id = "_" + idx

            def loc(fmt, underscore=True):
                if blank:
                    plural = ""
                else:
                    plural = "s"
                return fmt.format(plural, row_id if underscore else row_id.lstrip("_"))

            def remove(loc):
                """Return a callable that clicks but still allows popup dismissal"""
                return lambda _: sel.click(loc, wait_ajax=False)

            return Form(
                fields=[('name_text', Input(loc('field{}_name{}'))),
                        ('type_select', {
                            version.LOWEST: DHTMLSelect(loc("//div[@id='field{}_aetype_id{}']")),
                            "5.5": AngularSelect(loc("field{}_aetype{}", underscore=False))}),
                        ('data_type_select', {
                            version.LOWEST: DHTMLSelect(loc("//div[@id='field{}_datatype_id{}']")),
                            "5.5": AngularSelect(loc("field{}_datatype{}", underscore=False))}),
                        ('default_value_text', Input(loc('field{}_default_value{}'))),
                        ('display_name_text', Input(loc('field{}_display_name{}'))),
                        ('description_text', Input(loc('field{}_description{}'))),
                        ('sub_cb', Input(loc('field{}_substitution{}'))),
                        ('collect_text', Input(loc('field{}_collect{}'))),
                        ('message_text', Input(loc('field{}_message{}'))),
                        ('on_entry_text', Input(loc('field{}_on_entry{}'))),
                        ('on_exit_text', Input(loc('field{}_on_exit{}'))),
                        ('max_retries_text', Input(loc('field{}_max_retries{}'))),
                        ('max_time_text', Input(loc('field{}_max_time{}'))),
                        ('add_entry_button', "//img[@alt='Add this entry']"),
                        ('remove_entry_button', remove(
                            "//a[(contains(@title, 'delete this') or "
                            "contains(@confirm, 'delete field')) and "
                            "contains(@href, 'arr_id={}')]/img".format(idx)))])

    schema_edit_page = Region(locators={
        'add_field_btn': "//img[@alt='Equal green']"})

    def edit_schema(self, add_fields=None, remove_fields=None):
        navigate_to(self, 'SchemaEdit')
        for remove_field in remove_fields or []:
            f = remove_field.get_form()
            fill(f, {}, action=f.remove_entry_button, action_always=True)

        for add_field in add_fields or []:
            sel.click(self.schema_edit_page.add_field_btn)
            f = add_field.get_form(blank=True)
            fill(f, {'name_text': add_field.name,
                     'type_select': add_field.type_,
                     'data_type_select': add_field.data_type,
                     'default_value_text': add_field.default_value,
                     'description_text': add_field.description,
                     'sub_cb': add_field.sub,
                     'collect_text': add_field.collect,
                     'message_text': add_field.message,
                     'on_entry_text': add_field.on_entry,
                     'on_exit_text': add_field.on_exit,
                     'max_retries_text': add_field.max_retries,
                     'max_time_text': add_field.max_time},
                 action=f.add_entry_button)

        sel.click(form_buttons.save)
        flash.assert_success_message('Schema for Automate Class "{}" was saved'.format(self.name))


@navigator.register(Class, 'Add')
class ClassNew(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        cfg_btn('Add a New Class')

    def am_i_here(self):
        return match_location(summary='Adding a new Class')


@navigator.register(Class, 'Details')
class ClassDetails(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        table_click(self.obj.display_name or self.obj.name, 'ae_class')

    def am_i_here(self):
        return match_location(summary='Automate Class "{}"'.format(self.obj.name_in_table))


@navigator.register(Class, 'Edit')
class ClassEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Class')

    def am_i_here(self):
        return match_location(summary='Editing Class "{}"'.format(self.obj.name))


@navigator.register(Class, 'SchemaEdit')
class ClassSchemaEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        select_tab('Schema')
        cfg_btn('Edit selected Schema')

    def am_i_here(self):
        return match_location(summary='Editing Class Schema "{}"'.format(self.obj.name))


class Method(Navigatable, CopiableTreeNode, Updateable):
    """Represents a Method in the CFME ui.  `Display Name` is not
       supported (it causes the name to be displayed differently in
       different places in the UI). """

    # TODO These locators need updating once the multiename Input class goes in

    form = Form(
        fields=[('name_text', "//input[contains(@name,'method_name')]"),
                ('display_name_text', "//input[contains(@name,'method_display_name')]"),
                ('data_text', ScriptBox(
                    ta_locator="//textarea[@id='method_data' or @id='cls_method_data']"))])

    def __init__(
            self, name=None, display_name=None, location=None, data=None, cls=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        # TODO: display name
        self.display_name = None
        self.location = location
        self.data = data
        self.cls = cls

    @property
    def parent(self):
        return self.cls

    @parent.setter
    def parent(self, p):
        self.cls = p

    def create(self, cancel=False, allow_duplicate=False):
        if self.parent is not None and not self.parent.exists():
            self.parent.create()
        if self.exists() and not allow_duplicate:
            return
        navigate_to(self, 'Add')
        fill(self.form, {'name_text': self.name,
                         # 'display_name_text': self.display_name,
                         'data_text': self.data},
             action=form_buttons.cancel if cancel else form_buttons.add)
        try:
            flash.assert_success_message('Automate Method "{}" was added'.format(self.name))
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(form_buttons.cancel)
            raise

    def update(self, updates, cancel=False):
        navigate_to(self, 'Edit')
        fill(self.form, {'name_text': updates.get('name'),
                         'description_text': updates.get('description'),
                         'data_text': updates.get('data')})
        if not cancel:
            if form_buttons.save.is_dimmed:
                # Fire off the handlers manually
                self.form.data_text.workaround_save_issue()
            sel.click(form_buttons.save)
        else:
            sel.click(form_buttons.cancel)

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        cfg_btn('Remove this Method', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()


@navigator.register(Method, 'Add')
class MethodNew(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        select_tab('Methods')
        cfg_btn('Add a New Method')

    def am_i_here(self):
        return match_location(summary='Adding a new Automate Method')


@navigator.register(Method, 'Details')
class MethodDetails(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        select_tab('Methods')
        table_click(self.obj.display_name or self.obj.name, 'ae_method')

    def am_i_here(self):
        if not match_location():
            return False
        summary = summary_title()
        return (
            summary.startswith('Automate Method [{} - Updated'.format(self.obj.display_name)) or
            summary.startswith('Automate Method [{} - Updated'.format(self.obj.name))
        )


@navigator.register(Method, 'Edit')
class MethodEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Method')

    def am_i_here(self):
        return match_location(summary='Editing Automate Method "{}"'.format(self.obj.name))


class InstanceFieldsRow(pretty.Pretty):
    """Represents one row of instance fields.

    Args:
        row_id: Sequential id of the row (begins with 0)
    """
    table = Table("//div[@id='form_div']//table[thead]")
    columns = ("value", "on_entry", "on_exit", "on_error", "collect")
    fields = (
        "inst_value_{}", "inst_on_entry_{}", "inst_on_exit_{}",
        "inst_on_error_{}", "inst_collect_{}"
    )
    pretty_attrs = ['_row_id']

    def __init__(self, row_id):
        self._row_id = row_id

    @property
    def form(self):
        """Returns the form with fields targeted at our row_id.

        Does not need to be on the page.
        """
        return Form(fields=[
            (
                col_name,
                "//input[contains(@id, '{}')]".format(self.fields[i].format(self._row_id))
            )
            for i, col_name
            in enumerate(self.columns)
        ])


class InstanceFields(object):
    """Represents the table of fields defined for instance.

    It uses web-scraping to determine what fields are available. It is maybe a slight slowdown, but
    no better solution with similar complexity (2 SLoC) exists.

    Only real drawback is that you cannot use `form` when being somewhere else than on the page.
    """
    fields = "//div[@id='class_instances_div']//table//tr/td[./ul[contains(@class, 'icons')]]"

    @property
    def form(self):
        """Returns Form filled with fields. Scraps the webpage to determine the fields.

        Requires to be on the page
        """
        names = []
        for cell in sel.elements(self.fields):
            # The received text is something like u'  (blabla)' so we extract 'blabla'
            sel.move_to_element(cell)  # This is required in order to correctly read the content
            names.append(re.sub(r"^[^(]*\(([^)]+)\)[^)]*$", "\\1", sel.text(cell).encode("utf-8")))
        return Form(fields=[(name, InstanceFieldsRow(i)) for i, name in enumerate(names)])


@fill.method((InstanceFields, Mapping))
def _fill_ifields_obj(ifields, d):
    logger.info("   Delegating the filling of the fields to the form.")
    return fill(ifields.form, d)


@fill.method((InstanceFieldsRow, Mapping))
def _fill_ifr_map(ifr, d):
    logger.info("   Filling row with data %s", str(d))
    return fill(ifr.form, dict(zip(ifr.columns, (d.get(x, None) for x in ifr.columns))))


@fill.method((InstanceFieldsRow, basestring))
def _fill_ifr_str(ifr, s):
    """You don't have to specify full dict when filling just value ..."""
    logger.info("   Filling row with value %s", s)
    return fill(ifr, {"value": s})


class Instance(Navigatable, CopiableTreeNode, Updateable):
    """Represents a Instance in the CFME ui."""

    form = Form(
        fields=[('name_text', "//input[contains(@name,'inst_name')]"),
                ('display_name_text', "//input[contains(@name,'inst_display_name')]"),
                ('description_text', "//input[contains(@name,'inst_description')]"),
                ('values', InstanceFields())])

    def __init__(
            self, name=None, display_name=None, description=None, values=None, cls=None,
            appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.values = values
        self.display_name = display_name
        self.cls = cls

    @property
    def name_in_tree(self):
        """The item is displayed differently with display_name"""
        if self.display_name:
            return "{} ({})".format(self.display_name, self.name)
        else:
            return self.name

    @property
    def name_in_table(self):
        """The item is displayed differently with display_name"""
        if self.display_name:
            return self.display_name
        else:
            return self.name

    @property
    def parent(self):
        return self.cls

    @parent.setter
    def parent(self, p):
        self.cls = p

    def create(self, cancel=False, allow_duplicate=False):
        if self.parent is not None and not self.parent.exists():
            self.parent.create()
        if self.exists() and not allow_duplicate:
            return
        navigate_to(self, 'Add')
        fill(self.form, {'name_text': self.name,
                         'display_name_text': self.display_name,
                         'description_text': self.description,
                         'values': self.values},
             action=form_buttons.cancel if cancel else form_buttons.add)
        try:
            flash.assert_success_message('Automate Instance "{}" was added'.format(self.name))
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(form_buttons.cancel)
            raise

    def update(self, updates, cancel=False):
        navigate_to(self, 'Edit')
        update_values = {
            'name_text': updates.get('name'),
            'description_text': updates.get('description'),
            'values': updates.get('values')}
        if "display_name" in updates:
            # We need to specifically override the display_name
            update_values["display_name_text"] = updates["display_name"] or ""  # None -> emptystr
        fill(
            self.form, update_values,
            action=form_buttons.cancel if cancel else form_buttons.save)

    def delete(self, cancel=False):
        navigate_to(self, 'Details')
        cfg_btn('Remove this Instance', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()


@navigator.register(Instance, 'Add')
class InstanceNew(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        select_tab('Instances')
        cfg_btn('Add a New Instance')

    def am_i_here(self):
        return match_location(summary='Adding a new Automate Instance')


@navigator.register(Instance, 'Details')
class InstanceDetails(CFMENavigateStep):
    prerequisite = NavigateToAttribute('parent', 'Details')

    def step(self):
        select_tab('Instances')
        table_click(self.obj.name_in_table, 'ae_instance')

    def am_i_here(self):
        if not match_location():
            return False
        summary = summary_title()
        return (
            summary.startswith('Automate Instance [{} - Updated'.format(self.obj.display_name)) or
            summary.startswith('Automate Instance [{} - Updated'.format(self.obj.name))
        )


@navigator.register(Instance, 'Edit')
class InstanceEdit(CFMENavigateStep):
    prerequisite = NavigateToSibling('Details')

    def step(self):
        cfg_btn('Edit this Instance')

    def am_i_here(self):
        return match_location(summary='Editing Automate Instance "{}"'.format(self.obj.name))
