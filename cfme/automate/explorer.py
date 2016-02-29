from copy import copy
from functools import partial
from xml.sax.saxutils import quoteattr

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui.menu import nav
import cfme.web_ui.flash as flash
import cfme.web_ui.toolbar as tb
from cfme.web_ui.tabstrip import select_tab
from cfme.web_ui import Form, Table, Tree, UpDownSelect, fill, Select, ScriptBox, DHTMLSelect,\
    Region, form_buttons, accordion, Input, AngularSelect
import cfme.exceptions as exceptions
from utils.update import Updateable
from utils import error, version, on_rtd
from collections import Mapping
import re
from utils.log import logger
from utils import classproperty, pretty
from utils.wait import wait_for

tree = Tree({
    version.LOWEST: '//table//tr[@title="Datastore"]/../..',
    '5.3': '//ul//a[@title="Datastore"]/../../..'})

datastore_tree = partial(accordion.tree, "Datastore", "Datastore")
cfg_btn = partial(tb.select, 'Configuration')


def datastore_checkbox(name):
    return version.pick({
        version.LOWEST: "//img[contains(@src, 'chk') and ../../td[normalize-space(.)={}]]",
        "5.5": "//input[@type='checkbox' and ../../td[normalize-space(.)={}]]"
    }).format(quoteattr(name))


def table_select(name):
    cb = datastore_checkbox(name)
    wait_for(sel.is_displayed, [cb], num_sec=5, delay=0.2)
    sel.check(datastore_checkbox(name))


def open_order_dialog_func(_):
    datastore_tree()
    cfg_btn("Edit Priority Order of Domains")

nav.add_branch(
    'automate_explorer',
    {
        'automate_explorer_tree_path':
        [lambda context:
            context.tree_item.navigate_tree() if context.tree_item is not None
            else tree.click_path('Datastore'),
         {
             'automate_explorer_table_select':
             [lambda ctx: table_select(ctx['table_item'].name_in_table),
              {
                  'automate_explorer_edit':
                  lambda context: context.tree_item.nav_edit(),
                  'automate_explorer_delete':
                  lambda _: cfg_btn('Remove selected Items', invokes_alert=True)}],

             'automate_explorer_namespace_new': lambda _: cfg_btn('Add a New Namespace'),
             'automate_explorer_domain_new': lambda _: cfg_btn('Add a New Domain'),
             'automate_explorer_class_new': lambda _: cfg_btn('Add a New Class'),
             "automate_explorer_domain_edit": lambda _: cfg_btn("Edit this Domain"),
             'automate_explorer_method_edit': lambda _: cfg_btn('Edit this Method'),
             'automate_explorer_instance_edit': lambda _: cfg_btn('Edit this Instance'),
             'automate_explorer_methods': [lambda _: select_tab('Methods'),
              {
                  'automate_explorer_method_new': lambda _: cfg_btn('Add a New Method'),
                  'automate_explorer_method_table_select':
                  lambda ctx: table_select(ctx['table_item'].name_in_table)}],

             'automate_explorer_instances': [lambda _: select_tab('Instances'),
              {
                  'automate_explorer_instance_new': lambda _: cfg_btn('Add a New Instance'),
                  'automate_explorer_instance_table_select':
                  lambda ctx: table_select(ctx['table_item'].name_in_table)}],

             'automate_explorer_schema': [lambda _: select_tab("Schema"),
             {
                 'automate_explorer_schema_edit': lambda _: cfg_btn("Edit selected Schema")
             }]}],
        "automate_explorer_domain_order": open_order_dialog_func,
    })


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
            sel.force_navigate('automate_explorer_tree_path', context={'tree_item': self})
        except exceptions.CandidateNotFound:
            return False
        else:
            return True

    @property
    def nav_path(self):
        return ["Datastore"] + self.path

    def navigate_tree(self):
        return tree.click_path(*self.nav_path)

    def nav_edit(self):
        dp_length = version.pick({version.LOWEST: 1,
                                  '5.3': 2})
        if len(self.nav_path) > dp_length:
            cfg_btn('Edit Selected Item')
        else:
            cfg_btn(version.pick({version.LOWEST: 'Edit Selected Namespaces',
                                  '5.3': 'Edit Selected Namespace'}))


class CopiableTreeNode(TreeNode):
    copy_form = Form(fields=[
        ("domain", {
            version.LOWEST: Select("select#domain"),
            "5.5": AngularSelect("domain")}),
        ("domain_text_only", {
            version.LOWEST: "//fieldset[p]//tr[./td[@class='key' and normalize-space(.)="
                            "'To Domain']]/td[not(@class='key') and not(select)]",
            "5.5": "//label[contains(@class, 'control-label') and normalize-space(.)='To Domain']/"
                   "../div/p"}),
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
            return self.__class__.__name__

    @class_name.setter
    def class_name(self, value):
        self._class_name = value

    def _open_copy_dialog(self):
        sel.force_navigate("automate_explorer_tree_path", context={"tree_item": self})
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
        flash.assert_message_match("Copy selected Automate {} was saved".format(self.class_name))

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


class Domain(TreeNode, Updateable):
    form = Form(fields=[('name', Input('ns_name')),
                        ('description', Input('ns_description')),
                        ('enabled', Input('ns_enabled'))])

    def __init__(self, name=None, description=None, enabled=False):
        self.name = name
        self.parent = None
        self.description = description
        self.enabled = enabled

    def create(self, cancel=False, allow_duplicate=False):
        if self.exists() and not allow_duplicate:
            return
        sel.force_navigate('automate_explorer_domain_new', context={'tree_item': self.parent})
        fill(self.form, {'name': self.name,
                         'description': self.description,
                         'enabled': self.enabled},
             action=form_buttons.cancel if cancel else form_buttons.add)

    def update(self, updates):
        sel.force_navigate("automate_explorer_domain_edit", context={"tree_item": self})
        fill(self.form, updates, action=form_buttons.save)
        flash.assert_no_errors()

    def delete(self, cancel=False):
        sel.force_navigate("automate_explorer_tree_path", context={"tree_item": self})
        cfg_btn("Remove this Domain", invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_message_match('Automate Domain "{}": Delete successful'.format(
            self.description or self.name))

    def _nav_orig(self):
        try:
            tree.click_path(*self.nav_path)
            return True, None
        except exceptions.CandidateNotFound as e:
            return False, e

    def _nav_locked(self):
        path = self.nav_path
        path[-1] = path[-1] + " (Locked)"  # Try the Locked version
        try:
            tree.click_path(*path)
            return True, None
        except exceptions.CandidateNotFound as e:
            return False, e

    def _nav_disabled(self):
        path = self.nav_path
        path[-1] = path[-1] + " (Disabled)"  # Try the Locked version
        try:
            tree.click_path(*path)
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
        sel.force_navigate("automate_explorer_tree_path", context={"tree_item": self})
        return (not self._nav_orig()[0]) and self._nav_locked()[0]

    @property
    def is_enabled(self):
        sel.force_navigate("automate_explorer_domain_edit", context={"tree_item": self})
        self.enabled = sel.element(self.form.enabled).is_selected()
        return self.enabled

    @classproperty
    def default(cls):
        if on_rtd:
            return cls('Default')
        else:
            if not hasattr(cls, "_default_domain"):
                cls._default_domain = version.pick({
                    version.LOWEST: None,
                    '5.3': cls('Default')
                })
            return cls._default_domain


domain_order_selector = UpDownSelect(
    "select#seq_fields",
    "//img[@alt='Move selected fields up']",
    "//img[@alt='Move selected fields down']")


def get_domain_order():
    sel.force_navigate("automate_explorer_domain_order")
    return domain_order_selector.get_items()


def set_domain_order(items):
    original_order = get_domain_order()
    # We pick only the same amount of items for comparing
    original_order = original_order[:len(items)]
    if items == original_order:
        return  # Ignore that, would cause error on Save click
    fill(domain_order_selector, items)
    sel.click(form_buttons.save)


class Namespace(TreeNode, Updateable):
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

    def __init__(self, name=None, description=None, parent=None, domain=None):
        self.name = name
        self.description = description
        self.parent = parent or (domain if isinstance(domain, Domain) else Domain.default)

    def create(self, cancel=False, allow_duplicate=False):
        if self.parent is not None and not self.parent.exists():
            self.parent.create()
        if self.exists() and not allow_duplicate:
            return
        sel.force_navigate('automate_explorer_namespace_new', context={'tree_item': self.parent})
        form_data = {'name': self.name,
                     'description': self.description}
        try:
            fill(self.form, form_data, action=form_buttons.cancel if cancel else form_buttons.add)
            flash.assert_success_message('Automate Namespace "%s" was added' % self.name)
        finally:
            # if there was a validation error we need to cancel out
            if sel.is_displayed(form_buttons.cancel):
                sel.click(form_buttons.cancel)

    def update(self, updates, cancel=False):
        sel.force_navigate('automate_explorer_edit', context={'tree_item': self.parent,
                                                              'table_item': self})
        form_data = {'name': updates.get('name') or None,
                     'description': updates.get('description') or None}
        fill(self.form, form_data, action=form_buttons.cancel if cancel else form_buttons.save)
        flash.assert_success_message('Automate Namespace "%s" was saved' %
                                     updates.get('name', self.name))

    def delete(self, cancel=False):
        sel.force_navigate("automate_explorer_table_select", context={'tree_item': self.parent,
                                                                      'table_item': self})
        dp_length = version.pick({version.LOWEST: 1,
                                  '5.3': 2})
        if len(self.path) > dp_length:
            cfg_btn('Remove selected Items', invokes_alert=True)
        else:
            cfg_btn('Remove Namespaces', invokes_alert=True)
        sel.handle_alert(cancel)
        del_msg = version.pick({
            version.LOWEST: 'The selected Automate Namespaces were deleted',
            '5.3': 'Automate Namespace "{}": Delete successful'.format(self.description)
        })
        flash.assert_success_message(del_msg)

    def __repr__(self):
        return "<%s.%s name=%s, path=%s>" % (__name__, self.__class__.__name__,
                                             self.name, self.path)


class Class(CopiableTreeNode, Updateable):
    """Represents a Class in the CFME ui.

    Providing a setup_schema dict, creates the Class with teh specified schema

    """

    form = Form(fields=[('name_text', Input('name')),
                        ('display_name_text', Input('display_name')),
                        ('description_text', Input('description')),
                        ('inherits_from_select', Select("//select[@name='inherits_from']"))])

    def __init__(self, name=None, display_name=None, description=None, inherits_from=None,
                 namespace=None, setup_schema=None):
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
        if version.current_version() < "5.4":
            return path
        else:
            return "/" + path  # Starts with / from 5.4 onwards because of domains

    def create(self, cancel=False, allow_duplicate=False):
        if self.parent is not None and not self.parent.exists():
            self.parent.create()
        if self.exists() and not allow_duplicate:
            return
        sel.force_navigate("automate_explorer_class_new", context={"tree_item": self.namespace})
        fill(self.form, {'name_text': self.name,
                         'description_text': self.description,
                         'display_name_text': self.display_name,
                         'inherits_from_select':
                         self.inherits_from and self.inherits_from.path_str()},
             action=form_buttons.cancel if cancel else form_buttons.add)
        flash.assert_success_message('Automate Class "%s" was added' % self.path_str())
        if self.setup_schema:
            self.edit_schema(add_fields=self.setup_schema)

    def update(self, updates, cancel=False):
        sel.force_navigate("automate_explorer_edit", context={"tree_item": self.parent,
                                                     "table_item": self})
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
        sel.force_navigate("automate_explorer_delete", context={'tree_item': self.parent,
                                                                'table_item': self})
        sel.handle_alert(cancel)
        return flash.assert_no_errors()

    class SchemaField(Updateable):
        def __init__(self, name=None, type_=None, data_type=None, default_value=None,
                     display_name=None, description=None, sub=None, collect=None, message=None,
                     on_entry=None, on_exit=None, on_error=None, max_retries=None, max_time=None):
            self.name = name
            self.type_ = type_
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
                idx = sel.get_attribute("//input[starts-with(@id, 'fields_name') and @value='%s']" %
                                    self.name, 'id').split("_")[-1]
                row_id = "_" + idx

            def loc(fmt, underscore=True):
                if blank:
                    plural = ""
                else:
                    plural = "s"
                return fmt % (plural, row_id if underscore else row_id.lstrip("_"))

            def remove(loc):
                """Return a callable that clicks but still allows popup dismissal"""
                return lambda _: sel.click(loc, wait_ajax=False)

            return Form(
                fields=[('name_text', Input(loc('field%s_name%s'))),
                        ('type_select', {
                            version.LOWEST: DHTMLSelect(loc("//div[@id='field%s_aetype_id%s']")),
                            "5.5": AngularSelect(loc("field%s_aetype%s", underscore=False))}),
                        ('data_type_select', {
                            version.LOWEST: DHTMLSelect(loc("//div[@id='field%s_datatype_id%s']")),
                            "5.5": AngularSelect(loc("field%s_datatype%s", underscore=False))}),
                        ('default_value_text', Input(loc('field%s_default_value%s'))),
                        ('display_name_text', Input(loc('field%s_display_name%s'))),
                        ('description_text', Input(loc('field%s_description%s'))),
                        ('sub_cb', Input(loc('field%s_substitution%s'))),
                        ('collect_text', Input(loc('field%s_collect%s'))),
                        ('message_text', Input(loc('field%s_message%s'))),
                        ('on_entry_text', Input(loc('field%s_on_entry%s'))),
                        ('on_exit_text', Input(loc('field%s_on_exit%s'))),
                        ('max_retries_text', Input(loc('field%s_max_retries%s'))),
                        ('max_time_text', Input(loc('field%s_max_time%s'))),
                        ('add_entry_button', "//img[@alt='Add this entry']"),
                        ('remove_entry_button', remove(
                            "//a[(contains(@title, 'delete this') or "
                            "contains(@confirm, 'delete field')) and "
                            "contains(@href, 'arr_id=%s')]/img" % idx))])

    schema_edit_page = Region(locators={
        'add_field_btn': {
            version.LOWEST: "//img[@alt='Equal-green']",
            "5.5.0.7": "//img[@alt='Equal green']"}})

    def edit_schema(self, add_fields=None, remove_fields=None):
        sel.force_navigate("automate_explorer_schema_edit", context={'tree_item': self})
        for remove_field in remove_fields or []:
            f = remove_field.get_form()
            fill(f, {}, action=f.remove_entry_button, action_always=True)
            if version.current_version() < "5.5.0.7":
                sel.handle_alert()

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
        flash.assert_success_message('Schema for Automate Class "%s" was saved' % self.name)


class Method(CopiableTreeNode, Updateable):
    """Represents a Method in the CFME ui.  `Display Name` is not
       supported (it causes the name to be displayed differently in
       different places in the UI). """

    # TODO These locators need updating once the multiename Input class goes in

    form = Form(
        fields=[('name_text', "//input[contains(@name,'method_name')]"),
                ('display_name_text', "//input[contains(@name,'method_display_name')]"),
                ('data_text', ScriptBox(
                    ta_locator="//textarea[@id='method_data' or @id='cls_method_data']"))])

    def __init__(self, name=None, display_name=None, location=None, data=None, cls=None):
        self.name = name
        # self.display_name = display_name
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
        sel.force_navigate("automate_explorer_method_new", context={'tree_item': self.cls})
        fill(self.form, {'name_text': self.name,
                         # 'display_name_text': self.display_name,
                         'data_text': self.data},
             action=form_buttons.cancel if cancel else form_buttons.add)
        try:
            flash.assert_success_message('Automate Method "%s" was added' % self.name)
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(form_buttons.cancel)
            raise

    def update(self, updates, cancel=False):
        sel.force_navigate("automate_explorer_method_edit", context={"tree_item": self})
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
        sel.force_navigate("automate_explorer_tree_path", context={'tree_item': self})
        cfg_btn('Remove this Method', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()


class InstanceFieldsRow(pretty.Pretty):
    """Represents one row of instance fields.

    Args:
        row_id: Sequential id of the row (begins with 0)
    """
    table = Table({
        version.LOWEST: "//div[@id='form_div']//table[@class='style3']",
        "5.4": "//div[@id='form_div']//table[thead]"})
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
    fields = {
        version.LOWEST: "//div[@id='form_div']//table[@class='style3']//td[img]",
        "5.4": "//div[@id='form_div']//table[thead]//td[img]",
        "5.5": "//div[@id='class_instances_div']//table//tr/td[./ul[contains(@class, 'icons')]]",
    }

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
    logger.info("   Filling row with data {}".format(str(d)))
    return fill(ifr.form, dict(zip(ifr.columns, (d.get(x, None) for x in ifr.columns))))


@fill.method((InstanceFieldsRow, basestring))
def _fill_ifr_str(ifr, s):
    """You don't have to specify full dict when filling just value ..."""
    logger.info("   Filling row with value {}".format(s))
    return fill(ifr, {"value": s})


class Instance(CopiableTreeNode, Updateable):
    """Represents a Instance in the CFME ui."""

    form = Form(
        fields=[('name_text', "//input[contains(@name,'inst_name')]"),
                ('display_name_text', "//input[contains(@name,'inst_display_name')]"),
                ('description_text', "//input[contains(@name,'inst_description')]"),
                ('values', InstanceFields())])

    def __init__(self, name=None, display_name=None, description=None, values=None, cls=None):
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
        sel.force_navigate("automate_explorer_instance_new", context={'tree_item': self.cls})
        fill(self.form, {'name_text': self.name,
                         'display_name_text': self.display_name,
                         'description_text': self.description,
                         'values': self.values},
             action=form_buttons.cancel if cancel else form_buttons.add)
        try:
            flash.assert_success_message('Automate Instance "%s" was added' % self.name)
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(form_buttons.cancel)
            raise

    def update(self, updates, cancel=False):
        sel.force_navigate("automate_explorer_instance_edit", context={"tree_item": self})
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
        sel.force_navigate("automate_explorer_tree_path", context={'tree_item': self})
        cfg_btn('Remove this Instance', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()
