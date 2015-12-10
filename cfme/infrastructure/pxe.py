# -*- coding: utf-8 -*-
""" A model of a PXE Server in CFME
"""

from functools import partial

from cfme.exceptions import CandidateNotFound
import cfme.fixtures.pytest_selenium as sel
import cfme.web_ui.accordion as acc
import cfme.web_ui.flash as flash
from cfme.web_ui.menu import nav
import cfme.web_ui.toolbar as tb
from cfme.web_ui import fill, InfoBlock, Region, Form, ScriptBox, Select, Table, form_buttons, Input
from cfme.web_ui import paginator as pg
from selenium.common.exceptions import NoSuchElementException
import utils.conf as conf
from utils.datafile import load_data_file
from utils.log import logger
from utils.path import project_path
from utils.update import Updateable
from utils.wait import wait_for
from utils import version
from utils.pretty import Pretty
from utils.db import cfmedb
from utils.varmeth import variable

cfg_btn = partial(tb.select, 'Configuration')

pxe_server_table_exist = Table('//div[@id="records_div"]/table/tbody/tr/td')
pxe_details_page = Region(locators=dict(
    last_refreshed=InfoBlock("Basic Information", "Last Refreshed On"),
    pxe_image_type=InfoBlock("Basic Information", "Type")
))

pxe_properties_form = Form(
    fields=[
        ('name_text', Input('name')),
        ('log_protocol', Select("//select[@id='log_protocol']")),
        ('uri_text', Input('uri')),
        ('userid_text', Input('log_userid')),
        ('password_text', Input('log_password')),
        ('verify_text', Input('log_verify')),
        ('validate_btn', "//a[@id='val']"),
        ('access_url_text', Input('access_url')),
        ('pxe_dir_text', Input('pxe_directory')),
        ('windows_dir_text', Input('windows_images_directory')),
        ('customize_dir_text', Input('customization_directory')),
        ('pxe_menu_text', Input('pxemenu_0')),
    ])

pxe_image_type_form = Form(
    fields=[
        ('image_type', Select("//select[@id='image_typ']"))
    ])


template_details_page = Region(infoblock_type='form')  # infoblock shoudl be type 'detail' #gofigure

template_properties_form = Form(
    fields=[
        ('name_text', Input('name')),
        ('description_text', Input('description')),
        ('image_type', Select('//select[@id="img_typ"]')),
        ('script_type', Select('//select[@id="typ"]')),
        ('script_data', ScriptBox(ta_locator="//textarea[@id='script_data']"))
    ])


image_table = Table('//div[@id="records_div"]//table')

image_properties_form = Form(
    fields=[
        ('name_text', Input('name')),
        ('provision_type', Select('//select[@id="provision_type"]'))
    ])

iso_details_page = Region(infoblock_type='form')  # infoblock shoudl be type 'detail' #gofigure

iso_properties_form = Form(
    fields=[
        ('provider', Select('//select[@id="ems_id"]')),
    ])

iso_image_type_form = Form(
    fields=[
        ('image_type', Select("//select[@id='image_typ']"))
    ])


pxe_tree = partial(acc.tree, "PXE Servers", "All PXE Servers")
template_tree = partial(acc.tree, "Customization Templates",
                        "All Customization Templates - System Image Types")
image_tree = partial(acc.tree, "System Image Types", "All System Image Types")
iso_tree = partial(acc.tree, "ISO Datastores", "All ISO Datastores")


nav.add_branch('infrastructure_pxe',
               {'infrastructure_pxe_servers': [lambda _: pxe_tree(),
                {'infrastructure_pxe_server_new': lambda _: cfg_btn('Add a New PXE Server'),
                 'infrastructure_pxe_server': [lambda ctx: pxe_tree(ctx.pxe_server.name),
                                               {'infrastructure_pxe_server_edit':
                                                lambda _: cfg_btn('Edit this PXE Server')}]}],

                'infrastructure_pxe_templates': [lambda _: template_tree(),
                {'infrastructure_pxe_template_new':
                 lambda _: cfg_btn('Add a New Customization Template'),
                 'infrastructure_pxe_template':
                 [lambda ctx: template_tree(ctx.pxe_template.image_type, ctx.pxe_template.name),
                  {'infrastructure_pxe_template_edit':
                   lambda _: cfg_btn('Edit this Customization Template')}]}],

                'infrastructure_pxe_image_types': [lambda _: image_tree(),
                {'infrastructure_pxe_image_type_new':
                 lambda _: cfg_btn('Add a new System Image Type'),
                 'infrastructure_pxe_image_type':
                 [lambda ctx: image_table.click_cell('name', ctx.pxe_image_type.name),
                  {'infrastructure_pxe_image_type_edit':
                   lambda _: cfg_btn('Edit this System Image Type')}]}],

                'infrastructure_iso_datastores': [lambda _: iso_tree(),
                {'infrastructure_iso_datastore_new':
                 lambda _: cfg_btn('Add a New ISO Datastore'),
                 'infrastructure_iso_datastore':
                 lambda ctx: iso_tree(ctx.pxe_iso_datastore.provider)}]})


class PXEServer(Updateable, Pretty):
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
            sel.click(form_buttons.cancel)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, refresh=True, refresh_timeout=120):
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
        self._submit(cancel, form_buttons.add)
        if not cancel:
            flash.assert_message_match('PXE Server "{}" was added'.format(self.name))
            if refresh:
                self.refresh(timeout=refresh_timeout)
        else:
            flash.assert_message_match('Add of new PXE Server was cancelled by the user')

    @variable(alias="db")
    def exists(self):
        """
        Checks if the PXE server already exists
        """
        dbs = cfmedb()
        candidates = list(dbs.session.query(dbs["pxe_servers"]))
        return self.name in [s.name for s in candidates]

    @exists.variant('ui')
    def exists_ui(self):
        """
        Checks if the PXE server already exists
        """
        sel.force_navigate('infrastructure_pxe_servers')
        try:
            pxe_tree(self.name)
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

        sel.force_navigate('infrastructure_pxe_server_edit', context={"pxe_server": self})
        fill(pxe_properties_form, self._form_mapping(**updates))
        self._submit(cancel, form_buttons.save)
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

        sel.force_navigate('infrastructure_pxe_server', context={"pxe_server": self})
        cfg_btn('Remove this PXE Server from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        if not cancel:
            flash.assert_message_match('PXE Server "{}": Delete successful'.format(self.name))

    def refresh(self, wait=True, timeout=120):
        """ Refreshes the PXE relationships and waits for it to be updated
        """
        sel.force_navigate('infrastructure_pxe_server', context={"pxe_server": self})
        ref_time = lambda: pxe_details_page.last_refreshed.text
        last_time = ref_time()
        cfg_btn('Refresh Relationships', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_match(
            'PXE Server "{}": Refresh Relationships successfully initiated'.format(self.name))
        if wait:
            wait_for(lambda lt: lt != ref_time(),
                     func_args=[last_time], fail_func=sel.refresh, num_sec=timeout,
                     message="pxe refresh")

    @variable(alias='db')
    def get_pxe_image_type(self, image_name):
        pxe_i = cfmedb()["pxe_images"]
        pxe_s = cfmedb()["pxe_servers"]
        pxe_t = cfmedb()["pxe_image_types"]
        hosts = list(cfmedb().session.query(pxe_t.name)
                     .join(pxe_i, pxe_i.pxe_image_type_id == pxe_t.id)
                     .join(pxe_s, pxe_i.pxe_server_id == pxe_s.id)
                     .filter(pxe_s.name == self.name)
                     .filter(pxe_i.name == image_name))
        if hosts:
            return hosts[0][0]
        else:
            return None

    @get_pxe_image_type.variant('ui')
    def get_pxe_image_type(self, image_name):
        sel.force_navigate('infrastructure_pxe_servers')
        pxe_tree(self.name, 'PXE Images', image_name)
        return pxe_details_page.pxe_image_type.text

    def set_pxe_image_type(self, image_name, image_type):
        """
        Function to set the image type of a PXE image
        """
        if self.get_pxe_image_type(image_name) != image_type:
            sel.force_navigate('infrastructure_pxe_servers')
            pxe_tree(self.name, 'PXE Images', image_name)
            cfg_btn('Edit this PXE Image')
            fill(pxe_image_type_form, {'image_type': image_type}, action=form_buttons.save)


class CustomizationTemplate(Updateable, Pretty):
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
            sel.click(form_buttons.cancel)
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
        self._submit(cancel, form_buttons.add)
        if not cancel:
            flash.assert_message_match(
                version.pick({
                    version.LOWEST: 'Customization Template "{}" was added'.format(self.name),
                    '5.3': 'Customization Template "{}" was saved'.format(self.name)
                }))
        else:
            flash.assert_message_match(
                'Add of new Customization Template was cancelled by the user')

    @variable(alias='db')
    def exists(self):
        """
        Checks if the Customization template already exists
        """
        dbs = cfmedb()
        candidates = list(dbs.session.query(dbs["customization_templates"]))
        return self.name in [s.name for s in candidates]

    @exists.variant('ui')
    def exists_ui(self):
        """
        Checks if the Customization template already exists
        """
        sel.force_navigate('infrastructure_pxe_templates')
        try:
            template_tree(self.image_type, self.name)
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

        sel.force_navigate('infrastructure_pxe_template_edit', context={"pxe_template": self})
        fill(template_properties_form, self._form_mapping(**updates))
        self._submit(cancel, form_buttons.save)
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

        sel.force_navigate('infrastructure_pxe_template', context={"pxe_template": self})
        cfg_btn('Remove this Customization Template from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_message_match(
            'Customization Template "{}": Delete successful'.format(self.description))


class SystemImageType(Updateable, Pretty):
    """Model of a System Image Type in CFME.

    Args:
        name: The name of the System Image Type.
        provision_type: The provision type, either Vm or Host.
    """
    pretty_attrs = ['name', 'provision_type']

    def __init__(self, name=None, provision_type=None):
        self.name = name
        self.provision_type = provision_type

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'provision_type': kwargs.get('provision_type')}

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(form_buttons.cancel)
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
        self._submit(cancel, form_buttons.add)
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

        sel.force_navigate('infrastructure_pxe_image_type_edit', context={"pxe_image_type": self})
        fill(image_properties_form, self._form_mapping(**updates))
        self._submit(cancel, form_buttons.save)
        # No flash message

    def delete(self, cancel=True):
        """
        Deletes a System Image Type from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_pxe_image_type', context={"pxe_image_type": self})
        cfg_btn('Remove this System Image Type from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_message_match('System Image Type "{}": Delete successful'.format(self.name))


class ISODatastore(Updateable, Pretty):
    """Model of a PXE Server object in CFME

    Args:
        provider: Provider name.
    """
    pretty_attrs = ['provider']

    def __init__(self, provider=None):
        self.provider = provider

    def _form_mapping(self, create=None, **kwargs):
        return {'provider': kwargs.get('provider')}

    def _submit(self, cancel, submit_button):
        if cancel:
            sel.click(form_buttons.cancel)
            # sel.wait_for_element(page.configuration_btn)
        else:
            sel.click(submit_button)
            flash.assert_no_errors()

    def create(self, cancel=False, refresh=True, refresh_timeout=120):
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
        self._submit(cancel, form_buttons.add)
        flash.assert_message_match('ISO Datastore "{}" was added'.format(self.provider))
        if refresh:
            self.refresh(timeout=refresh_timeout)

    @variable(alias='db')
    def exists(self):
        """
        Checks if the ISO Datastore already exists via db
        """
        iso = cfmedb()['iso_datastores']
        ems = cfmedb()['ext_management_systems']
        name = self.provider
        iso_ds = list(cfmedb().session.query(iso.id)
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
        sel.force_navigate('infrastructure_iso_datastores')
        try:
            iso_tree(self.provider)
            return True
        except CandidateNotFound:
            return False

    def delete(self, cancel=True):
        """
        Deletes an ISO Datastore from CFME

        Args:
            cancel: Whether to cancel the deletion, defaults to True
        """

        sel.force_navigate('infrastructure_iso_datastore', context={"pxe_iso_datastore": self})
        cfg_btn('Remove this ISO Datastore from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=cancel)
        flash.assert_message_match('ISO Datastore "{}": Delete successful'.format(self.provider))

    def refresh(self, wait=True, timeout=120):
        """ Refreshes the PXE relationships and waits for it to be updated
        """
        sel.force_navigate('infrastructure_iso_datastore', context={"pxe_iso_datastore": self})
        ref_time = lambda: pxe_details_page.last_refreshed.text
        last_time = ref_time()
        cfg_btn('Refresh Relationships', invokes_alert=True)
        sel.handle_alert()
        flash.assert_message_match(
            'ISO Datastore "{}": Refresh Relationships successfully initiated'
            .format(self.provider))
        if wait:
            wait_for(lambda lt: lt != ref_time(),
                     func_args=[last_time], fail_func=sel.refresh, num_sec=timeout,
                     message="iso refresh")

    def set_iso_image_type(self, image_name, image_type):
        """
        Function to set the image type of a PXE image
        """
        sel.force_navigate('infrastructure_iso_datastores')
        iso_tree(self.provider, 'ISO Images', image_name)
        cfg_btn('Edit this ISO Image')
        fill(iso_image_type_form, {'image_type': image_type})
        # Click save if enabled else click Cancel
        try:
            sel.click(form_buttons.save)
        except:
            sel.click(form_buttons.cancel)


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
    logger.debug('Removing all PXE servers')
    sel.force_navigate('infrastructure_pxe_servers')
    sel.force_navigate('infrastructure_pxe_servers')  # Yes we really do this twice.
    if sel.is_displayed(pxe_server_table_exist):
        sel.click(pg.check_all())
        cfg_btn('Remove PXE Servers from the VMDB', invokes_alert=True)
        sel.handle_alert(cancel=False)
