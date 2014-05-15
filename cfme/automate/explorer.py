from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui.menu import nav
import cfme.web_ui.flash as flash
import cfme.web_ui.toolbar as tb
from cfme.web_ui.tabstrip import select_tab
from cfme.web_ui import Form, Tree, fill, Select, ScriptBox, DHTMLSelect, Region
import cfme.exceptions as exceptions
from utils.update import Updateable
import utils.error as error

tree = sel.ver_pick({'default': Tree('//table//tr[@title="Datastore"]/../..'),
                     '9.9.9.9': Tree('//div[@id="ae_treebox"]/ul')})
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
    if len(path) > 1:
        cfg_btn('Edit Selected Item')
    else:
        cfg_btn('Edit Selected Namespaces')


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
                  lambda _: cfg_btn('Remove selected Items', invokes_alert=True)
              }],
             'automate_explorer_namespace_new': lambda _: cfg_btn('Add a New Namespace'),
             'automate_explorer_class_new': lambda _: cfg_btn('Add a New Class'),
             'automate_explorer_method_edit': lambda _: cfg_btn('Edit this Method'),
             'automate_explorer_instance_edit': lambda _: cfg_btn('Edit this Instance'),
             'automate_explorer_methods': [lambda _: select_tab('Methods'),
              {
                  'automate_explorer_method_new': lambda _: cfg_btn('Add a New Method'),
                  'automate_explorer_method_table_select':
                  lambda ctx: table_select(ctx['table_item'].name)
              }],
             'automate_explorer_instances': [lambda _: select_tab('Instances'),
              {
                  'automate_explorer_instance_new': lambda _: cfg_btn('Add a New Instance'),
                  'automate_explorer_instance_table_select':
                  lambda ctx: table_select(ctx['table_item'].name)
              }],
             'automate_explorer_schema': [lambda _: select_tab("Schema"),
             {
                 'automate_explorer_schema_edit': lambda _: cfg_btn("Edit selected Schema")
             }]
         }]
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


class Namespace(TreeNode, Updateable):
    form = Form(fields=
                [('name', "//*[@id='ns_name']"),
                 ('description', "//*[@id='ns_description']"),
                 ('add_btn', "//ul[@id='form_buttons']/li/img[@alt='Add']")]
                + submit_and_cancel_buttons)

    create_btn_map = {True: form.cancel_btn, False: form.add_btn}
    update_btn_map = {True: form.cancel_btn, False: form.save_btn}

    @staticmethod
    def make_path(*names):
        """
        Make a set of nested Namespace objects with the given path.

        Usage:
            #eg.
                n = Namespace.make_path("foo", "bar")
            #is equivalent to:
                n = Namespace(name="bar", parent=Namespace(name="foo"))
        """

        if names:
            names = list(names)
            return Namespace(name=names.pop(), parent=Namespace.make_path(*names))
        else:
            return None

    def __init__(self, name=None, description=None, parent=None):
        self.name = name
        self.description = description
        self.parent = parent

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
        if len(self.path) > 1:
            cfg_btn('Remove selected Items', invokes_alert=True)
        else:
            cfg_btn('Remove Namespaces', invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_message_contain('Delete successful')
        flash.assert_success_message('The selected Automate Namespaces were deleted')

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
                fields=
                [('name_text', loc("//input[@id='field%s_name%s']")),
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
                  remove("//a[contains(@title, 'delete this') and contains(@href, 'arr_id=%s')]"
                         % idx))])

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
                ('data_text', ScriptBox("//textarea[contains(@name,'method_data')]"))]
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


class Instance(TreeNode, Updateable):
    """Represents a Instance in the CFME ui.  `Display Name` is not
       supported (it causes the name to be displayed differently in
       different places in the UI). """

    form = Form(
        fields=[('name_text', "//input[contains(@name,'inst_name')]"),
                ('display_name_text', "//input[contains(@name,'inst_display_name')]"),
                ('description_text', "//input[contains(@name,'inst_description')]")]
        + submit_and_cancel_buttons)

    def __init__(self, name=None, display_name=None, description=None, cls=None):
        self.name = name
        self.description = description
        # self.display_name = display_name
        self.cls = cls

    @property
    def parent(self):
        return self.cls

    def create(self, cancel=False):
        sel.force_navigate("automate_explorer_instance_new", context={'tree_item': self.cls})
        fill(self.form, {'name_text': self.name,
                         # 'display_name_text': self.display_name,
                         'description_text': self.description},
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
                         'description_text': updates.get('description')},
             action={True: self.form.cancel_btn, False: self.form.save_btn}[cancel])

    def delete(self, cancel=False):
        sel.force_navigate("automate_explorer_tree_path", context={'tree_item': self})
        cfg_btn('Remove this Instance', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()
