from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui.menu import nav
import cfme.web_ui.flash as flash
import cfme.web_ui.toolbar as tb
from cfme.web_ui.tabstrip import select_tab
from cfme.web_ui import Form, Table, Tree, fill, Select, ScriptBox, DHTMLSelect, Region
import cfme.exceptions as exceptions
from utils.update import Updateable
from utils import error, version
from collections import Mapping
import re
from utils.log import logger

tree = Tree(version.pick({version.LOWEST: '//table//tr[@title="Datastore"]/../..',
                         '5.3': '//ul//a[@title="Datastore"]/../../..'}))
cfg_btn = partial(tb.select, 'Configuration')

submit_and_cancel_buttons = [('add_btn', "//ul[@id='form_buttons']/li/img[@alt='Add']"),
                           ('save_btn', "//ul[@id='form_buttons']/li/img[@alt='Save Changes']"),
                           ('cancel_btn', "//ul[@id='form_buttons']/li/img[@alt='Cancel']")]


def datastore_checkbox(name):
    return "//img[contains(@src, 'chk') and ../../td[.='%s']]" % name


def nav_tree_item(path):
    tree.click_path(*path)


def table_select(name):
    sel.check(datastore_checkbox(name))


def nav_edit(path):
    dp_length = version.pick({version.LOWEST: 1,
                              '5.3': 2})
    if len(path) > dp_length:
        cfg_btn('Edit Selected Item')
    else:
        cfg_btn(version.pick({version.LOWEST: 'Edit Selected Namespaces',
                              '5.3': 'Edit Selected Namespace'}))


def get_path(o):
    # prepend the top level "Datastore"
    p = getattr(o, 'path', [])
    return ["Datastore"] + p


def tree_item_not_found_is_leaf(e):
    """Returns true if the given exception was while navigating a tree and
       the item in the path that was missing was the last item."""
    data = e.args[0]  # the data mapping
    return isinstance(e, exceptions.CandidateNotFound) and data['index'] == len(data['path']) - 1

nav.add_branch(
    'automate_explorer',
    {
        'automate_explorer_tree_path':
        [lambda ctx: nav_tree_item(get_path(ctx['tree_item'])),
         {
             'automate_explorer_table_select':
             [lambda ctx: table_select(ctx['table_item'].name),
              {
                  'automate_explorer_edit':
                  lambda ctx: nav_edit(get_path(ctx['tree_item'])),
                  'automate_explorer_delete':
                  lambda _: cfg_btn('Remove selected Items', invokes_alert=True)}],

             'automate_explorer_namespace_new': lambda _: cfg_btn('Add a New Namespace'),
             'automate_explorer_domain_new': lambda _: cfg_btn('Add a New Domain'),
             'automate_explorer_class_new': lambda _: cfg_btn('Add a New Class'),
             'automate_explorer_method_edit': lambda _: cfg_btn('Edit this Method'),
             'automate_explorer_instance_edit': lambda _: cfg_btn('Edit this Instance'),
             'automate_explorer_methods': [lambda _: select_tab('Methods'),
              {
                  'automate_explorer_method_new': lambda _: cfg_btn('Add a New Method'),
                  'automate_explorer_method_table_select':
                  lambda ctx: table_select(ctx['table_item'].name)}],

             'automate_explorer_instances': [lambda _: select_tab('Instances'),
              {
                  'automate_explorer_instance_new': lambda _: cfg_btn('Add a New Instance'),
                  'automate_explorer_instance_table_select':
                  lambda ctx: table_select(ctx['table_item'].name)}],

             'automate_explorer_schema': [lambda _: select_tab("Schema"),
             {
                 'automate_explorer_schema_edit': lambda _: cfg_btn("Edit selected Schema")
             }]}]
    })


class TreeNode(object):
    @property
    def path(self):
        """Returns the path to this object as a list starting from the root"""
        # A node with no name is the root node
        if self.parent:
            return list(self.parent.path) + [self.name]
        else:
            return [self.name]

    def exists(self):
        with error.handler(tree_item_not_found_is_leaf):
            sel.force_navigate('automate_explorer_tree_path', context={'tree_item': self})
            return True
        return False

    def __repr__(self):
        return "<%s name=%s>" % (self.__class__.__name__, self.name)


class Domain(TreeNode):
    form = Form(fields=[('name', "//input[@id='ns_name']"),
                        ('description', "//input[@id='ns_description']"),
                        ('enabled', "//input[@id='ns_enabled']")]
                + submit_and_cancel_buttons)
    create_btn_map = {True: form.cancel_btn, False: form.add_btn}

    def __init__(self, name=None, description=None, enabled=False):
        self.name = name
        self.parent = None
        self.description = description
        self.enabled = enabled

    def create(self, cancel=False):
        sel.force_navigate('automate_explorer_domain_new', context={'tree_item': self.parent})
        fill(self.form, {'name': self.name,
                         'description': self.description,
                         'enabled': self.enabled},
             action=self.create_btn_map[cancel])


def_domain = version.pick({version.LOWEST: None,
                           '5.3': Domain('Default')})


class Namespace(TreeNode, Updateable):
    form = Form(fields=[('name', "//*[@id='ns_name']"),
                        ('description', "//*[@id='ns_description']"),
                        ('add_btn', "//ul[@id='form_buttons']/li/img[@alt='Add']")]
                + submit_and_cancel_buttons)

    create_btn_map = {True: form.cancel_btn, False: form.add_btn}
    update_btn_map = {True: form.cancel_btn, False: form.save_btn}

    @staticmethod
    def make_path(*names, **kwargs):
        """
        Make a set of nested Namespace objects with the given path.

        Usage:
            #eg.
                n = Namespace.make_path("foo", "bar")
            #is equivalent to:
                n = Namespace(name="bar", parent=Namespace(name="foo"))
        """

        domain = kwargs.get('domain', None)

        if len(names) == 1 and domain:
            names = list(names)
            return Namespace(name=names.pop(), parent=domain)
        elif names:
            names = list(names)
            if domain:
                return Namespace(name=names.pop(),
                                 parent=Namespace.make_path(domain=domain, *names))
            else:
                return Namespace(name=names.pop(), parent=Namespace.make_path(*names))
        else:
            return None

    def __init__(self, name=None, description=None, parent=None, domain=def_domain):
        self.name = name
        self.description = description
        self.parent = parent or domain

    def create(self, cancel=False):
        sel.force_navigate('automate_explorer_namespace_new', context={'tree_item': self.parent})
        form_data = {'name': self.name,
                     'description': self.description}
        try:
            fill(self.form, form_data, action=self.create_btn_map[cancel])
            flash.assert_success_message('Automate Namespace "%s" was added' % self.name)
        finally:
            # if there was a validation error we need to cancel out
            if sel.is_displayed(self.form.cancel_btn):
                sel.click(self.form.cancel_btn)

    def update(self, updates, cancel=False):
        sel.force_navigate('automate_explorer_edit', context={'tree_item': self.parent,
                                                              'table_item': self})
        form_data = {'name': updates.get('name') or None,
                     'description': updates.get('description') or None}
        fill(self.form, form_data, action=self.update_btn_map[cancel])
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


class Class(TreeNode, Updateable):
    """Represents a Class in the CFME ui.  `Display Name` is not supported
       (it causes the name to be displayed differently in different
       places in the UI)."""

    form = Form(fields=[('name_text', "//input[@name='name']"),
                        ('display_name_text', "//input[@name='display_name']"),
                        ('description_text', "//input[@name='description']"),
                        ('inherits_from_select', Select("//select[@name='inherits_from']"))]
                + submit_and_cancel_buttons)

    def __init__(self, name=None, display_name=None, description=None, inherits_from=None,
                 namespace=None):
        self.name = name
        # self.display_name = display_name
        self.description = description
        self.inherits_from = inherits_from
        self.namespace = namespace

    @property
    def parent(self):
        return self.namespace

    def path_str(self):
        """Returns string path to this class, eg ns1/ns2/ThisClass"""
        return "/".join(self.path)

    def create(self, cancel=False):
        sel.force_navigate("automate_explorer_class_new", context={"tree_item": self.namespace})
        fill(self.form, {'name_text': self.name,
                         'description_text': self.description,
                         # 'display_name_text': self.display_name,
                         'inherits_from_select':
                         self.inherits_from and self.inherits_from.path_str()},
             action={True: self.form.cancel_btn, False: self.form.add_btn}[cancel])
        try:
            flash.assert_success_message('Automate Class "%s" was added' % self.path_str())
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(self.form.cancel_btn)
            raise

    def update(self, updates, cancel=False):
        sel.force_navigate("automate_explorer_edit", context={"tree_item": self.parent,
                                                     "table_item": self})
        fill(self.form, {'name_text': updates.get('name'),
                         'description_text': updates.get('description'),
                         # 'display_name_text': updates.get('display_name'),
                         'inherits_from_select':
                         updates.get('inherits_from') and updates.get('inherits_from').path_str()},
             action={True: self.form.cancel_btn, False: self.form.save_btn}[cancel])

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
                                    self.name, 'id').split("_")[2]
                row_id = "_" + idx

            def loc(fmt):
                if blank:
                    plural = ""
                else:
                    plural = "s"
                return fmt % (plural, row_id)

            def remove(loc):
                """Return a callable that clicks but still allows popup dismissal"""
                return lambda _: sel.click(loc, wait_ajax=False)

            return Form(
                fields=[('name_text', loc("//input[@id='field%s_name%s']")),
                        ('type_select', DHTMLSelect(loc("//div[@id='field%s_aetype_id%s']"))),
                        ('data_type_select',
                         DHTMLSelect(loc("//div[@id='field%s_datatype_id%s']"))),
                        ('default_value_text', loc("//input[@id='field%s_default_value%s']")),
                        ('display_name_text', loc("//input[@id='field%s_display_name%s']")),
                        ('description_text', loc("//input[@id='field%s_description%s']")),
                        ('sub_cb', loc("//input[@id='field%s_substitution%s']")),
                        ('collect_text', loc("//input[@id='field%s_collect%s']")),
                        ('message_text', loc("//input[@id='field%s_message%s']")),
                        ('on_entry_text', loc("//input[@id='field%s_on_entry%s']")),
                        ('on_exit_text', loc("//input[@id='field%s_on_exit%s']")),
                        ('max_retries_text', loc("//input[@id='field%s_max_retries%s']")),
                        ('max_time_text', loc("//input[@id='field%s_max_time%s']")),
                        ('add_entry_button', "//img[@alt='Add this entry']"),
                        ('remove_entry_button',
                         remove("//a[contains(@title, 'delete this') "
                                "and contains(@href, 'arr_id=%s')]/img" % idx))])

    schema_edit_page = Region(
        locators=dict({'add_field_btn': "//img[@alt='Equal-green']"}.items() +
                      submit_and_cancel_buttons))

    def edit_schema(self, add_fields=None, remove_fields=None):
        sel.force_navigate("automate_explorer_schema_edit", context={'tree_item': self})
        for remove_field in remove_fields or []:
            f = remove_field.get_form()
            fill(f, {}, action=f.remove_entry_button)
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

        sel.click(self.schema_edit_page.save_btn)
        flash.assert_success_message('Schema for Automate Class "%s" was saved' % self.name)


class Method(TreeNode, Updateable):
    """Represents a Method in the CFME ui.  `Display Name` is not
       supported (it causes the name to be displayed differently in
       different places in the UI). """

    form = Form(
        fields=[('name_text', "//input[contains(@name,'method_name')]"),
                ('display_name_text', "//input[contains(@name,'method_display_name')]"),
                ('data_text', ScriptBox("miqEditor"))]
        + submit_and_cancel_buttons)

    def __init__(self, name=None, display_name=None, location=None, data=None, cls=None):
        self.name = name
        # self.display_name = display_name
        self.location = location
        self.data = data
        self.cls = cls

    @property
    def parent(self):
        return self.cls

    def create(self, cancel=False):
        sel.force_navigate("automate_explorer_method_new", context={'tree_item': self.cls})
        fill(self.form, {'name_text': self.name,
                         # 'display_name_text': self.display_name,
                         'data_text': self.data},
             action={True: self.form.cancel_btn, False: self.form.add_btn}[cancel])
        try:
            flash.assert_success_message('Automate Method "%s" was added' % self.name)
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(self.form.cancel_btn)
            raise

    def update(self, updates, cancel=False):
        sel.force_navigate("automate_explorer_method_edit", context={"tree_item": self})
        fill(self.form, {'name_text': updates.get('name'),
                         'description_text': updates.get('description'),
                         'data_text': updates.get('data')},
             action={True: self.form.cancel_btn, False: self.form.save_btn}[cancel])

    def delete(self, cancel=False):
        sel.force_navigate("automate_explorer_tree_path", context={'tree_item': self})
        cfg_btn('Remove this Method', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()


class InstanceFieldsRow(object):
    """Represents one row of instance fields.

    Args:
        row_id: Sequential id of the row (begins with 0)
    """
    table = Table("//div[@id='form_div']//table[@class='style3']")
    columns = ("value", "on_entry", "on_exit", "on_error", "collect")
    fields = (
        "inst_value_{}", "inst_on_entry_{}", "inst_on_exit_{}",
        "inst_on_error_{}", "inst_collect_{}"
    )

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

    @property
    def form(self):
        """Returns Form filled with fields. Scraps the webpage to determine the fields.

        Requires to be on the page
        """
        names = []
        for cell in sel.elements("//div[@id='form_div']//table[@class='style3']//td[img]"):
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


class Instance(TreeNode, Updateable):
    """Represents a Instance in the CFME ui.  `Display Name` is not
       supported (it causes the name to be displayed differently in
       different places in the UI). """

    form = Form(
        fields=[('name_text', "//input[contains(@name,'inst_name')]"),
                ('display_name_text', "//input[contains(@name,'inst_display_name')]"),
                ('description_text', "//input[contains(@name,'inst_description')]"),
                ('values', InstanceFields())]
        + submit_and_cancel_buttons)

    def __init__(self, name=None, display_name=None, description=None, values=None, cls=None):
        self.name = name
        self.description = description
        self.values = values
        # self.display_name = display_name
        self.cls = cls

    @property
    def parent(self):
        return self.cls

    def create(self, cancel=False):
        sel.force_navigate("automate_explorer_instance_new", context={'tree_item': self.cls})
        fill(self.form, {'name_text': self.name,
                         # 'display_name_text': self.display_name,
                         'description_text': self.description,
                         'values': self.values},
             action={True: self.form.cancel_btn, False: self.form.add_btn}[cancel])
        try:
            flash.assert_success_message('Automate Instance "%s" was added' % self.name)
        except Exception as e:
            if error.match("Name has already been taken", e):
                sel.click(self.form.cancel_btn)
            raise

    def update(self, updates, cancel=False):
        sel.force_navigate("automate_explorer_instance_edit", context={"tree_item": self})
        fill(self.form, {'name_text': updates.get('name'),
                         # 'display_name_text': updates.get('display_name'),
                         'description_text': updates.get('description'),
                         'values': updates.get('values')},
             action={True: self.form.cancel_btn, False: self.form.save_btn}[cancel])

    def delete(self, cancel=False):
        sel.force_navigate("automate_explorer_tree_path", context={'tree_item': self})
        cfg_btn('Remove this Instance', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()
