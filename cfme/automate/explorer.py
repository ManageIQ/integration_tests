from functools import partial

import cfme.fixtures.pytest_selenium as sel
from cfme.web_ui.menu import nav
import cfme.web_ui.flash as flash
import cfme.web_ui.toolbar as tb
from cfme.web_ui import Form, Tree, fill, Select
from utils.log import logger
from utils.update import Updateable

tree = Tree('//table//tr[@title="Datastore"]/../..')
cfg_btn = partial(tb.select, 'Configuration')


def datastore_checkbox(name):
    return "//img[contains(@src, 'chk') and ../../td[.='%s']]" % name


def nav_namespace(path):
    logger.debug('Navigating the path')
    tree.click_path("Datastore", *path)


def nav_namespace_parent(path):
    nav_namespace(path[:-1])


def nav_add_namespace(path):
    nav_namespace_parent(path)
    cfg_btn('Add a New Namespace')


def nav_select(path):
    nav_namespace_parent(path)
    sel.check(datastore_checkbox(path[-1]))


def nav_edit_namespace(path):
    nav_select(path)
    if len(path) > 1:
        cfg_btn('Edit Selected Item')
    else:
        cfg_btn('Edit Selected Namespaces')


def nav_new_class(path):
    nav_namespace(path[:-1])
    cfg_btn('Add a New Class')


nav.add_branch(
    'automate_explorer',
    {
        'automate_explorer_add_ns': lambda ctx: nav_add_namespace(ctx['namespace'].path),
        'automate_explorer_edit_ns': lambda ctx: nav_edit_namespace(ctx['namespace'].path),
        'namespace': lambda ctx: nav_new_class(ctx['namespace'].path),
        'class': lambda ctx: nav_edit_namespace(ctx['class'].path)
    })


class Namespace(Updateable):
    form = Form(
        fields=[
            ('name', "//*[@id='ns_name']"),
            ('description', "//*[@id='ns_description']"),
            ('add_btn', "//ul[@id='form_buttons']/li/img[@alt='Add']"),
            ('save_btn', "//ul[@id='form_buttons']/li/img[@alt='Save Changes']"),
            ('cancel_btn', "//ul[@id='form_buttons']/li/img[@alt='Cancel']"),
        ])

    create_btn_map = {True: form.cancel_btn, False: form.add_btn}
    update_btn_map = {True: form.cancel_btn, False: form.save_btn}

    def __init__(self, name=None, description=None, path=None):
        self.name = name
        self.description = description
        self._path = path or []

    @property
    def path(self):
        return list(self._path) + [self.name]  # because name can be changed

    def create(self, cancel=False):
        nav.go_to('automate_explorer_add_ns', context={'namespace': self})
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
        nav.go_to('automate_explorer_edit_ns', context={'namespace': self})
        form_data = {'name': updates.get('name') or None,
                     'description': updates.get('description') or None}
        fill(self.form, form_data, action=self.update_btn_map[cancel])
        flash.assert_success_message('Automate Namespace "%s" was saved' %
                                     updates.get('name', self.name))

    def delete(self, cancel=False):
        nav.go_to("automate_explorer")
        nav_select(self.path)
        if len(self.path) > 1:
            cfg_btn('Remove selected Items', invokes_alert=True)
        else:
            cfg_btn('Remove Namespaces', invokes_alert=True)
        sel.handle_alert(cancel)
        flash.assert_message_contain('Delete successful')
        flash.assert_success_message('The selected Automate Namespaces were deleted')

    def exists(self):
        try:
            nav.go_to('automate_explorer_edit_ns', context={'namespace': self})
            return True
        except:
            return False

    def __repr__(self):
        return "<%s.%s name=%s, path=%s>" % (__name__, self.__class__.__name__,
                                             self.name, self.path)


class Class(Updateable):
    form = Form(
        fields=[('name_text', "//input[@name='name']"),
                ('display_name_text', "//input[@name='display_name']"),
                ('description_text', "//input[@name='description']"),
                ('inherits_from_select', Select("//select[@name='inherits_from']")),
                ('add_btn', "//ul[@id='form_buttons']/li/img[@alt='Add']"),
                ('save_btn', "//ul[@id='form_buttons']/li/img[@alt='Save Changes']"),
                ('cancel_btn', "//ul[@id='form_buttons']/li/img[@alt='Cancel']")])

    def __init__(self, name=None, display_name=None, description=None, inherits_from=None,
                 namespace=None):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.inherits_from = inherits_from
        self.namespace = namespace
        self.path = namespace.path + [name]

    def path_str(self):
        """Returns string path to this class, eg ns1/ns2/ThisClass."""
        if self.namespace:
            p = self.namespace.path
        else:
            p = []
        p = p + [self.name]
        return "/".join(p)

    def create(self, cancel=False):
        nav.go_to("namespace", context={"namespace": self.namespace})
        fill(self.form, {'name_text': self.name,
                         'description_text': self.description,
                         'display_name_text': self.display_name,
                         'inherits_from_select':
                         self.inherits_from and self.inherits_from.path_str()},
             action={True: self.form.cancel_btn, False: self.form.add_btn}[cancel])

    def update(self, updates, cancel=False):
        nav.go_to("class", context={"class": self})
        fill(self.form, {'name_text': updates.get('name'),
                         'description_text': updates.get('description'),
                         'display_name_text': updates.get('display_name'),
                         'inherits_from_select':
                         updates.get('inherits_from') and updates.get('inherits_from').path_str()},
             action={True: self.form.cancel_btn, False: self.form.save_btn}[cancel])

    def delete(self, cancel=False):
        nav.go_to("automate_explorer")
        nav_select(self.path)
        cfg_btn('Remove selected Items', invokes_alert=True)
        sel.handle_alert(cancel)
        return flash.assert_no_errors()
