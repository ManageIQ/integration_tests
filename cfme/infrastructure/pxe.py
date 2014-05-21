""" A model of a PXE Server in CFME
"""

from functools import partial

from cfme.exceptions import CandidateNotFound
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.accordion as acc
import cfme.web_ui.flash as flash
from cfme.web_ui.menu import nav
import cfme.web_ui.toolbar as tb
from cfme.web_ui import fill, Region, Form, ScriptBox, Select, Table, Tree, form_buttons
from cfme.web_ui import paginator as pg
from selenium.common.exceptions import NoSuchElementException
import utils.conf as conf
from utils.datafile import load_data_file
from utils.log import logger
from utils.path import project_path
from utils.update import Updateable
from utils.wait import wait_for

cfg_btn = partial(tb.select, 'Configuration')

pxe_resetter = "//span[contains(., 'All PXE Servers')]"

pxe_server_table_exist = Table('//div[@id="records_div"]/table/tbody/tr/td')
pxe_server_tree = sel.ver_pick({'default': Tree('//div[@id="pxe_servers_treebox"]//table'),
                                '9.9.9.9': Tree('//div[@id="pxe_servers_treebox"]//ul')})

pxe_details_page = Region(infoblock_type='form')  # infoblock shoudl be type 'detail' #gofigure

pxe_add_page = Region(
    locators={
        'add_btn': "//div[@id='buttons_on']//img[@alt='Add']",
        'cancel_btn': "//div[@id='buttons_on']//img[@alt='Cancel']",
    })

pxe_edit_page = Region(
    locators={
        'save_btn': "//div[@id='buttons_on']//img[@alt='Save Changes']",
        'cancel_btn': "//div[@id='buttons_on']//img[@alt='Cancel']",
    })

pxe_properties_form = Form(
    fields=[
        ('name_text', "//input[@id='name']"),
        ('log_protocol', Select("//select[@id='log_protocol']")),
        ('uri_text', "//input[@id='uri']"),
        ('userid_text', "//input[@id='log_userid']"),
        ('password_text', "//input[@id='log_password']"),
        ('verify_text', "//input[@id='log_verify']"),
        ('validate_btn', "//a[@id='val']"),
        ('access_url_text', "//input[@id='access_url']"),
        ('pxe_dir_text', "//input[@id='pxe_directory']"),
        ('windows_dir_text', "//input[@id='windows_images_directory']"),
        ('customize_dir_text', "//input[@id='customization_directory']"),
        ('pxe_menu_text', "//input[@id='pxemenu_0']"),
    ])

pxe_image_type_form = Form(
    fields=[
        ('image_type', Select("//select[@id='image_typ']"))
    ])

template_resetter = "//span[contains(., 'All Customization Templates - System Image Types')]"

template_tree = sel.ver_pick({
    'default': Tree('//div[@id="customization_templates_treebox"]//table'),
    '9.9.9.9': Tree('//div[@id="customization_templates_treebox"]//ul')
})

template_details_page = Region(infoblock_type='form')  # infoblock shoudl be type 'detail' #gofigure

template_add_button = sel.ver_pick({'default': form_buttons.add,
                                    '9.9.9.9': form_buttons.save})

template_add_page = Region(
    locators={
        'add_btn': "//div[@id='buttons_on']//img[@alt='Add']",
        'cancel_btn': "//div[@id='buttons_on']//img[@alt='Cancel']",
    })

template_edit_page = Region(
    locators={
        'save_btn': "//div[@id='buttons_on']//img[@alt='Save Changes']",
        'cancel_btn': "//div[@id='buttons_on']//img[@alt='Cancel']",
    })

template_properties_form = Form(
    fields=[
        ('name_text', "//input[@id='name']"),
        ('description_text', "//input[@id='description']"),
        ('image_type', Select('//select[@id="img_typ"]')),
        ('script_type', Select('//select[@id="typ"]')),
        ('script_data', ScriptBox("//textarea[@id='script_data']"))
    ])


image_resetter = "//span[contains(., 'All System Image Types')]"

image_table = Table('//div[@id="records_div"]//table')

image_add_page = Region(
    locators={
        'add_btn': "//div[@id='buttons_on']//img[@alt='Add']",
        'cancel_btn': "//div[@id='buttons_on']//img[@alt='Cancel']",
    })

image_edit_page = Region(
    locators={
        'save_btn': "//div[@id='buttons_on']//img[@alt='Save Changes']",
        'cancel_btn': "//div[@id='buttons_on']//img[@alt='Cancel']",
    })

image_properties_form = Form(
    fields=[
        ('name_text', "//input[@id='name']"),
        ('provision_type', Select('//select[@id="provision_type"]'))
    ])

iso_resetter = "//span[contains(., 'All ISO Datastores')]"

iso_details_page = Region(infoblock_type='form')  # infoblock shoudl be type 'detail' #gofigure

iso_properties_form = Form(
    fields=[
        ('provider', Select('//select[@id="ems_id"]')),
    ])

iso_tree = sel.ver_pick({
    'default': Tree('//div[@id="iso_datastores_treebox"]//table'),
    '9.9.9.9': Tree('//div[@id="iso_datastores_treebox"]//ul')
})

iso_image_type_form = Form(
    fields=[
        ('image_type', Select("//select[@id='image_typ']"))
    ])


def pxe_servers_pg():
    acc.click('PXE Servers')
    sel.click(sel.element(pxe_resetter))


def template_pg():
    acc.click('Customization Templates')
    sel.click(sel.element(template_resetter))


def system_image_pg():
    acc.click('System Image Types')
    sel.click(sel.element(image_resetter))


def iso_datastore_pg():
    acc.click('ISO Datastores')
    sel.click(sel.element(iso_resetter))


nav.add_branch('infrastructure_pxe',
               {'infrastructure_pxe_servers': [lambda _: pxe_servers_pg(),
                {'infrastructure_pxe_server_new': lambda _: cfg_btn('Add a New PXE Server'),
                 'infrastructure_pxe_server': [lambda ctx: pxe_server_tree.click_path(ctx.name),
                                               {'infrastructure_pxe_server_edit':
                                                lambda _: cfg_btn('Edit this PXE Server')}]}],

                'infrastructure_pxe_templates': [lambda _: template_pg(),
                {'infrastructure_pxe_template_new':
                 lambda _: cfg_btn('Add a New Customization Template'),
                 'infrastructure_pxe_template':
                 [lambda ctx: template_tree.click_path(ctx.image_type, ctx.name),
                  {'infrastructure_pxe_template_edit':
                   lambda _: cfg_btn('Edit this Customization Template')}]}],

                'infrastructure_pxe_image_types': [lambda _: system_image_pg(),
                {'infrastructure_pxe_image_type_new':
                 lambda _: cfg_btn('Add a new System Image Type'),
                 'infrastructure_pxe_image_type':
                 [lambda ctx: image_table.click_cell('name', ctx.name),
                  {'infrastructure_pxe_image_type_edit':
                   lambda _: cfg_btn('Edit this System Image Type')}]}],

                'infrastructure_iso_datastores': [lambda _: iso_datastore_pg(),
                {'infrastructure_iso_datastore_new':
                 lambda _: cfg_btn('Add a New ISO Datastore'),
                 'infrastructure_iso_datastore':
                 lambda ctx: iso_tree.click_path(ctx.provider)}]})


class PXEServer(Updateable):
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

    def __init__(self, name=None, depot_type=None, uri=None, userid=None, password=None,
                 access_url=None, pxe_dir=None, windows_dir=None, customize_dir=None,
                 menu_filename=None):
        self.name = name
        self.depot_type = depot_type
        self.uri = uri
        self.userid = userid
        self.password = password
        self.access_url = access_url
        self.pxe_dir = pxe_dir
        self.windows_dir = windows_dir
        self.customize_dir = customize_dir
        self.menu_filename = menu_filename

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'log_protocol': kwargs.get('depot_type'),
                'uri_text': kwargs.get('uri'),
                'password_text': kwargs.get('password'),
                'verify_text': kwargs.get('password'),
                'access_url_text': kwargs.get('access_url'),
                'pxe_dir_text': kwargs.get('pxe_dir'),
                'windows_dir_text': kwargs.get('windows_dir'),
                'customize_dir_text': kwargs.get('customize_dir'),
                'pxe_menu_text': kwargs.get('menu_filename')}

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(pxe_add_page.cancel_btn)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, refresh=True):
        """
        Creates a PXE server object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the PXE Server has been filled in the UI.
            refresh (boolean): Whether to run the refresh operation on the PXE server after
                the add has been completed.
        """
        sel.force_navigate('infrastructure_pxe_server_new')
        fill(pxe_properties_form, self._form_mapping(True, **self.__dict__))
        self._submit(cancel, pxe_add_page.add_btn)
        if not cancel:
            flash.assert_message_match('PXE Server "{}" was added'.format(self.name))
            if refresh:
                self.refresh()
        else:
            flash.assert_message_match('Add of new PXE Server was cancelled by the user')

    def exists(self):
        """
        Checks if the PXE server already exists
        """
        sel.force_navigate('infrastructure_pxe_servers')
        try:
            pxe_server_tree.click_path(self.name)
            return True
        except CandidateNotFound:
            return False
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

        sel.force_navigate('infrastructure_pxe_server_edit', context=self)
        fill(pxe_properties_form, self._form_mapping(**updates))
        self._submit(cancel, pxe_edit_page.save_btn)
        name = updates.get('name') or self.name
        if not cancel:
            flash.assert_message_match('PXE Server "{}" was saved'.format(name))
        else:
            flash.assert_message_match(
                'Edit of PXE Server "{}" was cancelled by the user'.format(name))

    def delete(self, cancel=True):
        """
        Deletes a PXE server from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_pxe_server', context=self)
        cfg_btn('Remove this PXE Server from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        if not cancel:
            flash.assert_message_match('PXE Server "{}": Delete successful'.format(self.name))

    def refresh(self, wait=True):
        """ Refreshes the PXE relationships and waits for it to be updated
        """
        sel.force_navigate('infrastructure_pxe_server', context=self)
        last_time = pxe_details_page.infoblock.text('Basic Information', 'Last Refreshed On')
        cfg_btn('Refresh Relationships', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_match(
            'PXE Server "{}": Refresh Relationships successfully initiated'.format(self.name))
        if wait:
            wait_for(lambda lt: lt != pxe_details_page.infoblock.text
                     ('Basic Information', 'Last Refreshed On'),
                     func_args=[last_time], fail_func=sel.refresh, num_sec=120)

    def set_pxe_image_type(self, image_name, image_type):
        """
        Function to set the image type of a PXE image
        """
        sel.force_navigate('infrastructure_pxe_servers')
        pxe_server_tree.click_path(self.name, 'PXE Images', image_name)
        cfg_btn('Edit this PXE Image')
        fill(pxe_image_type_form, {'image_type': image_type}, action=pxe_edit_page.save_btn)


class CustomizationTemplate(Updateable):
    """ Model of a Customization Template in CFME

    Args:
        name: The name of the template.
        description: Template description.
        image_type: Image type name, must be one of an existing System Image Type.
        script_type: Script type, either Kickstart, Cloudinit or Sysprep.
        script_data: The scripts data.
    """

    def __init__(self, name=None, description=None, image_type=None, script_type=None,
                 script_data=None):
        self.name = name
        self.description = description
        self.image_type = image_type
        self.script_type = script_type
        self.script_data = script_data

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'description_text': kwargs.get('description'),
                'image_type': kwargs.get('image_type'),
                'script_type': kwargs.get('script_type'),
                'script_data': kwargs.get('script_data')}

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(template_add_page.cancel_btn)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False):
        """
        Creates a Customization Template object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the CT has been filled in the UI.
        """
        sel.force_navigate('infrastructure_pxe_template_new')
        fill(template_properties_form, self._form_mapping(True, **self.__dict__))
        self._submit(cancel, template_add_button)
        if not cancel:
            flash.assert_message_match(
                sel.ver_pick({
                    'default': 'Customization Template "{}" was added'.format(self.name),
                    '9.9.9.9': 'Customization Template "{}" was saved'.format(self.name)
                }))
        else:
            flash.assert_message_match(
                'Add of new Customization Template was cancelled by the user')

    def exists(self):
        """
        Checks if the Customization template already exists
        """
        sel.force_navigate('infrastructure_pxe_templates')
        try:
            template_tree.click_path(self.image_type, self.name)
            return True
        except CandidateNotFound:
            return False
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

        sel.force_navigate('infrastructure_pxe_template_edit', context=self)
        fill(template_properties_form, self._form_mapping(**updates))
        self._submit(cancel, template_edit_page.save_btn)
        name = updates.get('name') or self.name
        if not cancel:
            flash.assert_message_match('Customization Template "{}" was saved'.format(name))
        else:
            flash.assert_message_match(
                'Edit of Customization Template "{}" was cancelled by the user'.format(name))

    def delete(self, cancel=True):
        """
        Deletes a Customization Template server from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_pxe_template', context=self)
        cfg_btn('Remove this Customization Template from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_message_match(
            'Customization Template "{}": Delete successful'.format(self.description))


class SystemImageType(Updateable):
    """Model of a System Image Type in CFME.

    Args:
        name: The name of the System Image Type.
        provision_type: The provision type, either Vm or Host.
    """

    def __init__(self, name=None, provision_type=None):
        self.name = name
        self.provision_type = provision_type

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'provision_type': kwargs.get('provision_type')}

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(image_add_page.cancel_btn)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False):
        """
        Creates a System Image Type object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the SIT has been filled in the UI.
        """
        sel.force_navigate('infrastructure_pxe_image_type_new')
        fill(image_properties_form, self._form_mapping(True, **self.__dict__))
        self._submit(cancel, image_add_page.add_btn)
        if not cancel:
            flash.assert_message_match('System Image Type "{}" was added'.format(self.name))
        else:
            flash.assert_message_match(
                'Add of new System Image Type was cancelled by the user')

    def update(self, updates, cancel=False):
        """
        Updates a System Image Type in the UI.  Better to use utils.update.update context
        manager than call this directly.

        Args:
           updates (dict): fields that are changing.
           cancel (boolean): whether to cancel out of the update.
        """

        sel.force_navigate('infrastructure_pxe_image_type_edit', context=self)
        fill(image_properties_form, self._form_mapping(**updates))
        self._submit(cancel, image_edit_page.save_btn)
        # No flash message

    def delete(self, cancel=True):
        """
        Deletes a System Image Type from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_pxe_image_type', context=self)
        cfg_btn('Remove this System Image Type from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_message_match('System Image Type "{}": Delete successful'.format(self.name))


class ISODatastore(Updateable):
    """Model of a PXE Server object in CFME

    Args:
        provider: Provider name.
    """

    def __init__(self, provider=None):
        self.provider = provider

    def _form_mapping(self, create=None, **kwargs):
        return {'provider': kwargs.get('provider')}

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(pxe_add_page.cancel_btn)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, refresh=True):
        """
        Creates an ISO datastore object

        Args:
            cancel (boolean): Whether to cancel out of the creation.  The cancel is done
                after all the information present in the ISO datastore has been filled in the UI.
            refresh (boolean): Whether to run the refresh operation on the ISO datastore after
                the add has been completed.
        """
        sel.force_navigate('infrastructure_iso_datastore_new')
        fill(iso_properties_form, self._form_mapping(True, **self.__dict__))
        self._submit(cancel, pxe_add_page.add_btn)
        flash.assert_message_match('ISO Datastore "{}" was added'.format(self.provider))
        if refresh:
            self.refresh()

    def exists(self):
        """
        Checks if the ISO Datastore already exists
        """
        sel.force_navigate('infrastructure_iso_datastores')
        try:
            iso_tree.click_path(self.provider)
            return True
        except CandidateNotFound:
            return False

    def delete(self, cancel=True):
        """
        Deletes an ISO Datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_iso_datastore', context=self)
        cfg_btn('Remove this ISO Datastore from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_message_match('ISO Datastore "{}": Delete successful'.format(self.provider))

    def refresh(self, wait=True):
        """ Refreshes the PXE relationships and waits for it to be updated
        """
        sel.force_navigate('infrastructure_iso_datastore', context=self)
        last_time = iso_details_page.infoblock.text('Basic Information', 'Last Refreshed On')
        cfg_btn('Refresh Relationships', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_match(
            'ISO Datastore "{}": Refresh Relationships successfully initiated'
            .format(self.provider))
        if wait:
            wait_for(lambda lt: lt != pxe_details_page.infoblock.text
                     ('Basic Information', 'Last Refreshed On'),
                     func_args=[last_time], fail_func=sel.refresh, num_sec=120)

    def set_iso_image_type(self, image_name, image_type):
        """
        Function to set the image type of a PXE image
        """
        sel.force_navigate('infrastructure_iso_datastores')
        iso_tree.click_path(self.provider, 'ISO Images', image_name)
        cfg_btn('Edit this ISO Image')
        fill(iso_image_type_form, {'image_type': image_type}, action=pxe_edit_page.save_btn)


def get_template_from_config(template_config_name):
    """
    Convenience function to grab the details for a template from the yamls.
    """

    template_config = conf.cfme_data['customization_templates'][template_config_name]

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

    pxe_config = conf.cfme_data['pxe_servers'][pxe_config_name]

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
    logger.debug('Removing all PXE servers')
    sel.force_navigate('infrastructure_pxe_servers')
    sel.force_navigate('infrastructure_pxe_servers')  # Yes we really do this twice.
    if sel.is_displayed(pxe_server_table_exist):
        sel.click(pg.check_all())
        cfg_btn('Remove PXE Servers from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=False)
