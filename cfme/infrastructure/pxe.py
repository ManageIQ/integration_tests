# -*- coding: utf-8 -*-
""" A model of a PXE Server in CFME
"""
from navmazing import NavigateToSibling, NavigateToAttribute
from selenium.common.exceptions import NoSuchElementException
from widgetastic.widget import View, Text, Checkbox
from widgetastic_manageiq import ManageIQTree, Input, ScriptBox, SummaryTable, Table
from widgetastic_patternfly import Dropdown, Accordion, FlashMessages, BootstrapSelect, Button

from cfme.base.login import BaseLoggedInPage
from cfme.utils.appliance import Navigatable
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from cfme.utils import conf
from cfme.utils.datafile import load_data_file
from cfme.utils.path import project_path
from cfme.utils.update import Updateable
from cfme.utils.wait import wait_for
from cfme.utils.pretty import Pretty
from cfme.utils.varmeth import variable


class PXEToolBar(View):
    """
    represents PXE toolbar and its controls
    """
    # todo: add back button later
    configuration = Dropdown(text='Configuration')


class PXESideBar(View):
    """
    represents left side bar. it usually contains navigation, filters, etc
    """
    @View.nested
    class servers(Accordion):  # noqa
        ACCORDION_NAME = "PXE Servers"
        tree = ManageIQTree()

    @View.nested
    class templates(Accordion):  # noqa
        ACCORDION_NAME = "Customization Templates"
        tree = ManageIQTree()

    @View.nested
    class image_types(Accordion):  # noqa
        ACCORDION_NAME = "System Image Types"
        tree = ManageIQTree()

    @View.nested
    class datastores(Accordion):  # noqa
        ACCORDION_NAME = "ISO Datastores"
        tree = ManageIQTree()


class PXEMainView(BaseLoggedInPage):
    """
    represents whole All PXE Servers page
    """
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    toolbar = View.nested(PXEToolBar)
    sidebar = View.nested(PXESideBar)
    title = Text('//div[@id="main-content"]//h1')
    entities = Table(locator='.//div[@id="records_div"]/table')

    @property
    def is_displayed(self):
        return self.navigation.currently_selected == ['Compute', 'Infrastructure', 'PXE']


class PXEServersView(PXEMainView):
    """
     represents whole All PXE Servers page
    """
    @property
    def is_displayed(self):
        return (super(PXEServersView, self).is_displayed and
                self.title.text == 'All PXE Servers')


class PXEDetailsToolBar(PXEToolBar):
    """
     represents the toolbar which appears when any pxe entity is clicked
    """
    reload = Button(title='Reload current display')


class PXEServerDetailsView(PXEMainView):
    """
     represents Server Details view
    """
    toolbar = View.nested(PXEDetailsToolBar)

    @View.nested
    class entities(View):  # noqa
        basic_information = SummaryTable(title="Basic Information")
        pxe_image_menus = SummaryTable(title='PXE Image Menus')

    @property
    def is_displayed(self):
        return False


class PXEServerForm(View):
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    # common fields
    name = Input(id='name')
    depot_type = BootstrapSelect(id='log_protocol')
    access_url = Input(id='access_url')
    pxe_dir = Input(id='pxe_directory')
    windows_images_dir = Input(id='windows_images_directory')
    customization_dir = Input(id='customization_directory')
    filename = Input(id='pxemenu_0')

    uri = Input(id='uri')  # both NFS and Samba

    # Samba only
    username = Input(id='log_userid')
    password = Input(id='log_password')
    confirm_password = Input(id='log_verify')
    validate = Button('Validate the credentials by logging into the Server')

    @property
    def is_displayed(self):
        return False


class PXEServerAddView(PXEServerForm):
    """
      represents Add New PXE Server view
    """
    add = Button('Add')
    cancel = Button('Cancel')


class PXEServerEditView(PXEServerForm):
    """
     represents PXE Server Edit view
    """
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class PXEImageEditView(View):
    """
    it can be found when some image is clicked in PXE Server Tree
    """
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    default_for_windows = Checkbox(id='default_for_windows')
    type = BootstrapSelect(id='image_typ')

    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')

    @property
    def is_displayed(self):
        return False


class PXEServer(Updateable, Pretty, Navigatable):
    """Model of a PXE Server object in CFME

    Args:
        name: Name of PXE server.
        depot_type: Depot type, either Samba or Network File System.
        uri: The Depot URI.
        userid: The Samba username.
        password: The Samba password.
        access_url: HTTP access path for PXE server.
        pxe_dir: The PXE dir for accessing configuration.
        windows_dir: Windows source directory.
        customize_dir: Customization directory for templates.
        menu_filename: Menu filename for iPXE/syslinux menu.
    """
    pretty_attrs = ['name', 'uri', 'access_url']

    def __init__(self, name=None, depot_type=None, uri=None, userid=None, password=None,
                 access_url=None, pxe_dir=None, windows_dir=None, customize_dir=None,
                 menu_filename=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.depot_type = depot_type
        self.uri = uri
        self.userid = userid
        # todo: turn into Credentials class
        self.password = password
        self.access_url = access_url
        self.pxe_dir = pxe_dir
        self.windows_dir = windows_dir
        self.customize_dir = customize_dir
        self.menu_filename = menu_filename

    def create(self, cancel=False, refresh=True, refresh_timeout=120):
        """
        Creates a PXE server object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the PXE Server has been filled in the UI.
            refresh (boolean): Whether to run the refresh operation on the PXE server after
                the add has been completed.
        """
        view = navigate_to(self, 'Add')
        view.fill({'name': self.name,
                   'depot_type': self.depot_type,
                   'access_url': self.access_url,
                   'pxe_dir': self.pxe_dir,
                   'windows_images_dir': self.windows_dir,
                   'customization_dir': self.customize_dir,
                   'filename': self.menu_filename,
                   'uri': self.uri,
                   # Samba only
                   'username': self.userid,
                   'password': self.password,
                   'confirm_password': self.password})
        if self.depot_type == 'Samba' and self.userid and self.password:
            view.validate.click()

        main_view = self.create_view(PXEServersView)
        if cancel:
            view.cancel.click()
            main_view.flash.assert_success_message('Add of new PXE Server '
                                                   'was cancelled by the user')
        else:
            view.add.click()
            main_view.flash.assert_success_message('PXE Server "{}" was added'.format(self.name))
            if refresh:
                self.refresh(timeout=refresh_timeout)

    @variable(alias="db")
    def exists(self):
        """
        Checks if the PXE server already exists
        """
        dbs = self.appliance.db.client
        candidates = list(dbs.session.query(dbs["pxe_servers"]))
        return self.name in [s.name for s in candidates]

    @exists.variant('ui')
    def exists_ui(self):
        """
        Checks if the PXE server already exists
        """
        try:
            navigate_to(self, 'Details')
            return True
        except NoSuchElementException:
            return False

    def update(self, updates, cancel=False):
        """
        Updates a PXE server in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        view = navigate_to(self, 'Edit')
        view.fill(updates)
        if updates.get('userid') or updates.get('password'):
            view.validate.click()

        name = updates.get('name') or self.name
        main_view = self.create_view(PXEServersView, override=updates)
        if cancel:
            view.cancel.click()
            main_view.flash.assert_success_message('Edit of PXE Server "{}" was '
                                                   'cancelled by the user'.format(name))
        else:
            view.save.click()
            main_view.flash.assert_success_message('PXE Server "{}" was saved'.format(name))

    def delete(self, cancel=True):
        """
        Deletes a PXE server from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this PXE Server', handle_alert=not cancel)
        if not cancel:
            main_view = self.create_view(PXEServersView)
            main_view.flash.assert_success_message('PXE Server "{}": '
                                                   'Delete successful'.format(self.name))
        else:
            navigate_to(self, 'Details')

    def refresh(self, wait=True, timeout=120):
        """ Refreshes the PXE relationships and waits for it to be updated
        """
        view = navigate_to(self, 'Details')
        last_time = view.entities.basic_information.get_text_of('Last Refreshed On')
        view.toolbar.configuration.item_select('Refresh Relationships', handle_alert=True)
        view.flash.assert_success_message('PXE Server "{}": Refresh Relationships '
                                          'successfully initiated'.format(self.name))
        if wait:
            basic_info = view.entities.basic_information
            wait_for(lambda lt: lt != basic_info.get_text_of('Last Refreshed On'),
                     func_args=[last_time], fail_func=view.toolbar.reload.click, num_sec=timeout,
                     message="pxe refresh")

    @variable(alias='db')
    def get_pxe_image_type(self, image_name):
        pxe_i = self.appliance.db.client["pxe_images"]
        pxe_s = self.appliance.db.client["pxe_servers"]
        pxe_t = self.appliance.db.client["pxe_image_types"]
        hosts = list(self.appliance.db.client.session.query(pxe_t.name)
                     .join(pxe_i, pxe_i.pxe_image_type_id == pxe_t.id)
                     .join(pxe_s, pxe_i.pxe_server_id == pxe_s.id)
                     .filter(pxe_s.name == self.name)
                     .filter(pxe_i.name == image_name))
        if hosts:
            return hosts[0][0]
        else:
            return None

    @get_pxe_image_type.variant('ui')
    def get_pxe_image_type_ui(self, image_name):
        view = navigate_to(self, 'Details')
        view.sidebar.servers.tree.click_path('All PXE Servers', self.name,
                                             'PXE Images', image_name)
        details_view = self.create_view(PXESystemImageTypeDetailsView)
        return details_view.entities.basic_information.get_text_of('Type')

    def set_pxe_image_type(self, image_name, image_type):
        """
        Function to set the image type of a PXE image
        """
        # todo: maybe create appropriate navmazing destinations instead ?
        if self.get_pxe_image_type(image_name) != image_type:
            view = navigate_to(self, 'Details')
            view.sidebar.servers.tree.click_path('All PXE Servers', self.name,
                                                 'PXE Images', image_name)
            details_view = self.create_view(PXESystemImageTypeDetailsView)
            details_view.toolbar.configuration.item_select('Edit this PXE Image')
            edit_view = self.create_view(PXEImageEditView)
            edit_view.fill({'type': image_type})
            edit_view.save.click()


@navigator.register(PXEServer, 'All')
class PXEServerAll(CFMENavigateStep):
    VIEW = PXEServersView
    prerequisite = NavigateToSibling('PXEMainPage')

    def step(self):
        self.view.sidebar.servers.tree.click_path('All PXE Servers')


@navigator.register(PXEServer, 'Add')
class PXEServerAdd(CFMENavigateStep):
    VIEW = PXEServerAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New PXE Server')


@navigator.register(PXEServer, 'Details')
class PXEServerDetails(CFMENavigateStep):
    VIEW = PXEServerDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.sidebar.servers.tree.click_path('All PXE Servers', self.obj.name)


@navigator.register(PXEServer, 'Edit')
class PXEServerEdit(CFMENavigateStep):
    VIEW = PXEServerEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this PXE Server')


class PXECustomizationTemplatesView(PXEMainView):
    """
    represents Customization Template Groups page
    """
    entities = Table(locator='.//div[@id="template_folders_div"]/table')

    @property
    def is_displayed(self):
        return (super(PXECustomizationTemplatesView, self).is_displayed and
                self.title.text == 'All Customization Templates - System Image Types')


class PXECustomizationTemplateDetailsView(PXEMainView):
    """
    represents some certain Customization Template Details page
    """
    toolbar = View.nested(PXEDetailsToolBar)

    @View.nested
    class entities(View):  # noqa
        basic_information = SummaryTable(title="Basic Information")
        script = ScriptBox(locator='//textarea[contains(@id, "script_data")]')

    @property
    def is_displayed(self):
        if getattr(self.context['object'], 'name'):
            title = 'Customization Template "{name}"'.format(self.context['object'].name)
            return (super(PXECustomizationTemplateDetailsView, self).is_displayed and
                    self.entities.title.text == title)
        else:
            return False


class PXECustomizationTemplateForm(View):
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    name = Input(id='name')
    description = Input(id='description')
    image_type = BootstrapSelect(id='img_typ')
    type = BootstrapSelect(id='typ')
    script = ScriptBox(locator='//textarea[contains(@id, "script_data")]')

    @property
    def is_displayed(self):
        return False


class PXECustomizationTemplateAddView(PXECustomizationTemplateForm):
    add = Button('Add')
    cancel = Button('Cancel')


class PXECustomizationTemplateEditView(PXECustomizationTemplateForm):
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class CustomizationTemplate(Updateable, Pretty, Navigatable):
    """ Model of a Customization Template in CFME

    Args:
        name: The name of the template.
        description: Template description.
        image_type: Image type name, must be one of an existing System Image Type.
        script_type: Script type, either Kickstart, Cloudinit or Sysprep.
        script_data: The scripts data.
    """
    pretty_attrs = ['name', 'image_type']

    def __init__(self, name=None, description=None, image_type=None, script_type=None,
                 script_data=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.description = description
        self.image_type = image_type
        self.script_type = script_type
        self.script_data = script_data

    def create(self, cancel=False):
        """
        Creates a Customization Template object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the CT has been filled in the UI.
        """
        view = navigate_to(self, 'Add')

        view.fill({'name': self.name,
                   'description': self.description,
                   'image_type': self.image_type,
                   'type': self.script_type,
                   'script': self.script_data})
        main_view = self.create_view(PXECustomizationTemplatesView)

        if cancel:
            view.cancel.click()
            msg = 'Add of new Customization Template was cancelled by the user'
        else:
            view.add.click()
            msg = 'Customization Template "{}" was saved'.format(self.name)
        main_view.flash.assert_success_message(msg)

    @variable(alias='db')
    def exists(self):
        """
        Checks if the Customization template already exists
        """
        dbs = self.appliance.db.client
        candidates = list(dbs.session.query(dbs["customization_templates"]))
        return self.name in [s.name for s in candidates]

    @exists.variant('ui')
    def exists_ui(self):
        """
        Checks if the Customization template already exists
        """
        try:
            navigate_to(self, 'Details')
            return True
        except NoSuchElementException:
            return False

    def update(self, updates, cancel=False):
        """
        Updates a Customization Template server in the UI.  Better to use utils.update.update
        context manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """
        view = navigate_to(self, 'Edit')
        view.fill(updates)
        main_view = self.create_view(PXECustomizationTemplatesView, override=updates)
        name = updates.get('name') or self.name

        if cancel:
            view.cancel.click()
            msg = 'Edit of Customization Template "{}" was cancelled by the user'.format(name)
        else:
            view.save.click()
            msg = 'Customization Template "{}" was saved'.format(name)
        main_view.flash.assert_success_message(msg)

    def delete(self, cancel=True):
        """
        Deletes a Customization Template server from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this Customization Template',
                                               handle_alert=cancel)
        if not cancel:
            main_view = self.create_view(PXECustomizationTemplatesView)
            msg = 'Customization Template "{}": Delete successful'.format(self.description)
            main_view.flash.assert_success_message(msg)
        else:
            navigate_to(self, 'Details')


@navigator.register(CustomizationTemplate, 'All')
class CustomizationTemplateAll(CFMENavigateStep):
    VIEW = PXECustomizationTemplatesView
    prerequisite = NavigateToSibling('PXEMainPage')

    def step(self):
        self.view.sidebar.templates.tree.click_path(('All Customization Templates - '
                                                     'System Image Types'))


@navigator.register(CustomizationTemplate, 'Add')
class CustomizationTemplateAdd(CFMENavigateStep):
    VIEW = PXECustomizationTemplateAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New Customization Template')


@navigator.register(CustomizationTemplate, 'Details')
class CustomizationTemplateDetails(CFMENavigateStep):
    VIEW = PXECustomizationTemplateDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        tree = self.view.sidebar.templates.tree
        tree.click_path('All Customization Templates - System Image Types', self.obj.image_type,
                        self.obj.name)


@navigator.register(CustomizationTemplate, 'Edit')
class CustomizationTemplateEdit(CFMENavigateStep):
    VIEW = PXECustomizationTemplateEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this Customization Template')


class PXESystemImageTypesView(PXEMainView):
    """
    represents whole All System Image Types page
    """

    @property
    def is_displayed(self):
        return (super(PXESystemImageTypesView, self).is_displayed and
                self.title.text == 'All System Image Types')


class PXESystemImageTypeDetailsView(PXEMainView):
    toolbar = View.nested(PXEDetailsToolBar)

    @View.nested
    class entities(View):  # noqa
        basic_information = SummaryTable(title="Basic Information")

    @property
    def is_displayed(self):
        return False


class PXESystemImageTypeForm(View):
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    name = Input(id='name')
    type = BootstrapSelect(id='provision_type')

    @property
    def is_displayed(self):
        return False


class PXESystemImageTypeAddView(PXESystemImageTypeForm):
    add = Button('Add')
    cancel = Button('Cancel')


class PXESystemImageTypeEditView(PXESystemImageTypeForm):
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class SystemImageType(Updateable, Pretty, Navigatable):
    """Model of a System Image Type in CFME.

    Args:
        name: The name of the System Image Type.
        provision_type: The provision type, either Vm or Host.
    """
    pretty_attrs = ['name', 'provision_type']
    VM_OR_INSTANCE = "VM and Instance"
    HOST_OR_NODE = "Host / Node"

    def __init__(self, name=None, provision_type=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.name = name
        self.provision_type = provision_type

    def create(self, cancel=False):
        """
        Creates a System Image Type object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the SIT has been filled in the UI.
        """
        view = navigate_to(self, 'Add')
        view.fill({'name': self.name, 'type': self.provision_type})
        main_view = self.create_view(PXESystemImageTypesView)
        if cancel:
            view.cancel.click()
            msg = 'Add of new System Image Type was cancelled by the user'
        else:
            view.add.click()
            msg = 'System Image Type "{}" was added'.format(self.name)
        main_view.flash.assert_success_message(msg)

    def update(self, updates, cancel=False):
        """
        Updates a System Image Type in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        view = navigate_to(self, 'Edit')
        view.fill({'name': updates.get('name'), 'type': updates.get('provision_type')})
        if cancel:
            view.cancel.click()
        else:
            view.save.click()
        # No flash message

    def delete(self, cancel=True):
        """
        Deletes a System Image Type from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """
        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this System Image Type',
                                               handle_alert=not cancel)
        if not cancel:
            main_view = self.create_view(PXESystemImageTypesView)
            msg = 'System Image Type "{}": Delete successful'.format(self.name)
            main_view.flash.assert_success_message(msg)
        else:
            navigate_to(self, 'Details')


@navigator.register(SystemImageType, 'All')
class SystemImageTypeAll(CFMENavigateStep):
    VIEW = PXESystemImageTypesView
    prerequisite = NavigateToSibling('PXEMainPage')

    def step(self):
        self.view.sidebar.image_types.tree.click_path('All System Image Types')


@navigator.register(SystemImageType, 'Add')
class SystemImageTypeAdd(CFMENavigateStep):
    VIEW = PXESystemImageTypeAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a new System Image Type')


@navigator.register(SystemImageType, 'Details')
class SystemImageTypeDetails(CFMENavigateStep):
    VIEW = PXESystemImageTypeDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.sidebar.image_types.tree.click_path('All System Image Types',
                                                                   self.obj.name)


@navigator.register(SystemImageType, 'Edit')
class SystemImageTypeEdit(CFMENavigateStep):
    VIEW = PXESystemImageTypeEditView
    prerequisite = NavigateToSibling('Details')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Edit this System Image Type')


class PXEDatastoresView(PXEMainView):
    """
    represents whole All ISO Datastores page
    """

    @property
    def is_displayed(self):
        return (super(PXEDatastoresView, self).is_displayed and
                self.title.text == 'All ISO Datastores')


class PXEDatastoreDetailsView(PXEMainView):
    toolbar = View.nested(PXEDetailsToolBar)

    @View.nested
    class entities(View):  # noqa
        basic_information = SummaryTable(title="Basic Information")

    @property
    def is_displayed(self):
        return False


class PXEDatastoreForm(View):
    title = Text('//div[@id="main-content"]//h1')
    flash = FlashMessages('.//div[@id="flash_msg_div"]/div[@id="flash_text_div" or '
                          'contains(@class, "flash_text_div")]')
    provider = BootstrapSelect(id='ems_id')

    @property
    def is_displayed(self):
        return False


class PXEDatastoreAddView(PXEDatastoreForm):
    add = Button('Add')
    cancel = Button('Cancel')


class PXEDatastoreEditView(PXEDatastoreForm):
    save = Button('Save')
    reset = Button('Reset')
    cancel = Button('Cancel')


class ISODatastore(Updateable, Pretty, Navigatable):
    """Model of a PXE Server object in CFME

    Args:
        provider: Provider name.
    """
    pretty_attrs = ['provider']

    def __init__(self, provider=None, appliance=None):
        Navigatable.__init__(self, appliance=appliance)
        self.provider = provider

    def create(self, cancel=False, refresh=True, refresh_timeout=120):
        """
        Creates an ISO datastore object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the ISO datastore has been filled in the UI.
            refresh (boolean): Whether to run the refresh operation on the ISO datastore after
                the add has been completed.
        """
        view = navigate_to(self, 'Add')
        view.fill({'provider': self.provider})
        main_view = self.create_view(PXEDatastoresView)
        if cancel:
            view.cancel.click()
            msg = 'Add of new ISO Datastore was cancelled by the user'
        else:
            view.add.click()
            msg = 'ISO Datastore "{}" was added'.format(self.provider)
        main_view.flash.assert_success_message(msg)

        if refresh:
            self.refresh(timeout=refresh_timeout)

    @variable(alias='db')
    def exists(self):
        """
        Checks if the ISO Datastore already exists via db
        """
        iso = self.appliance.db.client['iso_datastores']
        ems = self.appliance.db.client['ext_management_systems']
        name = self.provider
        iso_ds = list(self.appliance.db.client.session.query(iso.id)
                      .join(ems, iso.ems_id == ems.id)
                      .filter(ems.name == name))
        if iso_ds:
            return True
        else:
            return False

    @exists.variant('ui')
    def exists_ui(self):
        """
        Checks if the ISO Datastore already exists via UI
        """
        try:
            navigate_to(self, 'Details')
            return True
        except NoSuchElementException:
            return False

    def delete(self, cancel=True):
        """
        Deletes an ISO Datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        view = navigate_to(self, 'Details')
        view.toolbar.configuration.item_select('Remove this ISO Datastore', handle_alert=not cancel)
        if not cancel:
            main_view = self.create_view(PXEDatastoresView)
            msg = 'ISO Datastore "{}": Delete successful'.format(self.provider)
            main_view.flash.assert_success_message(msg)
        else:
            navigate_to(self, 'Details')

    def refresh(self, wait=True, timeout=120):
        """ Refreshes the PXE relationships and waits for it to be updated
        """
        view = navigate_to(self, 'Details')
        basic_info = view.entities.basic_information
        last_time = basic_info.get_text_of('Last Refreshed On')
        view.toolbar.configuration.item_select('Refresh Relationships', handle_alert=True)
        view.flash.assert_success_message(('ISO Datastore "{}": Refresh Relationships successfully '
                                           'initiated'.format(self.provider)))
        if wait:
            wait_for(lambda lt: lt != basic_info.get_text_of('Last Refreshed On'),
                     func_args=[last_time], fail_func=view.toolbar.reload.click, num_sec=timeout,
                     message="iso refresh")

    def set_iso_image_type(self, image_name, image_type):
        """
        Function to set the image type of a PXE image
        """
        view = navigate_to(self, 'All')
        view.sidebar.datastores.tree.click_path('All ISO Datastores', self.provider,
                                                'ISO Images', image_name)
        view.toolbar.configuration.item_select('Edit this ISO Image')
        view.fill({'image_type': image_type})
        # Click save if enabled else click Cancel
        if view.save.active:
            view.save.click()
        else:
            view.cancel.click()


@navigator.register(ISODatastore, 'All')
class ISODatastoreAll(CFMENavigateStep):
    VIEW = PXEDatastoresView
    prerequisite = NavigateToSibling('PXEMainPage')

    def step(self):
        self.view.sidebar.datastores.tree.click_path("All ISO Datastores")


@navigator.register(ISODatastore, 'Add')
class ISODatastoreAdd(CFMENavigateStep):
    VIEW = PXEDatastoreAddView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.prerequisite_view.toolbar.configuration.item_select('Add a New ISO Datastore')


@navigator.register(ISODatastore, 'Details')
class ISODatastoreDetails(CFMENavigateStep):
    VIEW = PXEDatastoreDetailsView
    prerequisite = NavigateToSibling('All')

    def step(self):
        self.view.sidebar.datastores.tree.click_path("All ISO Datastores", self.obj.provider)


@navigator.register(PXEServer, 'PXEMainPage')
@navigator.register(CustomizationTemplate, 'PXEMainPage')
@navigator.register(SystemImageType, 'PXEMainPage')
@navigator.register(ISODatastore, 'PXEMainPage')
class PXEMainPage(CFMENavigateStep):
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Compute', 'Infrastructure', 'PXE')


def get_template_from_config(template_config_name):
    """
    Convenience function to grab the details for a template from the yamls.
    """

    template_config = conf.cfme_data.get('customization_templates', {})[template_config_name]

    script_data = load_data_file(str(project_path.join(template_config['script_file'])),
                                 replacements=template_config['replacements'])

    script_data = script_data.read()

    return CustomizationTemplate(name=template_config['name'],
                                 description=template_config['description'],
                                 image_type=template_config['image_type'],
                                 script_type=template_config['script_type'],
                                 script_data=script_data)


def get_pxe_server_from_config(pxe_config_name):
    """
    Convenience function to grab the details for a pxe server fomr the yamls.
    """

    pxe_config = conf.cfme_data.get('pxe_servers', {})[pxe_config_name]

    return PXEServer(name=pxe_config['name'],
                     depot_type=pxe_config['depot_type'],
                     uri=pxe_config['uri'],
                     userid=pxe_config.get('userid') or None,
                     password=pxe_config.get('password') or None,
                     access_url=pxe_config['access_url'],
                     pxe_dir=pxe_config['pxe_dir'],
                     windows_dir=pxe_config['windows_dir'],
                     customize_dir=pxe_config['customize_dir'],
                     menu_filename=pxe_config['menu_filename'])


def remove_all_pxe_servers():
    """
    Convenience function to remove all PXE servers
    """
    view = navigate_to(PXEServer, 'All')
    if view.entities.is_displayed:
        for entity in view.entities.rows():
            entity[0].check()
        view.toolbar.configuration.item_select('Remove PXE Servers', handle_alert=True)
