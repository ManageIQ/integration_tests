"""Page model for Automation/Anisble/Credentials"""
import attr
from navmazing import NavigateToAttribute
from navmazing import NavigateToSibling
from widgetastic.exceptions import NoSuchElementException
from widgetastic.utils import ParametrizedLocator
from widgetastic.widget import ConditionalSwitchableView
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown
from widgetastic_patternfly import Input

from cfme.base import Server
from cfme.common import BaseLoggedInPage
from cfme.common import Taggable
from cfme.common import TagPageView
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection
from cfme.modeling.base import BaseEntity
from cfme.utils.appliance.implementations.ui import CFMENavigateStep
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.appliance.implementations.ui import navigator
from cfme.utils.wait import wait_for
from widgetastic_manageiq import PaginationPane
from widgetastic_manageiq import ParametrizedSummaryTable
from widgetastic_manageiq import Table


class CredentialsBaseView(BaseLoggedInPage):
    title = Text(locator=".//div[@id='main-content']//h1")

    @property
    def in_ansible_credentials(self):
        return (
            self.logged_in_as_current_user and
            self.navigation.currently_selected == ["Automation", "Ansible", "Credentials"]
        )


class CredentialsListView(CredentialsBaseView):
    @View.nested
    class toolbar(View):   # noqa
        configuration = Dropdown("Configuration")
        policy = Dropdown(text='Policy')

    credentials = Table(".//div[@id='miq-gtl-view']//table")
    paginator = PaginationPane()

    @property
    def is_displayed(self):
        return self.in_ansible_credentials and self.title.text == "Credentials"


class CredentialDetailsView(CredentialsBaseView):

    @View.nested
    class toolbar(View):  # noqa
        configuration = Dropdown("Configuration")
        download = Button(title="Print or export summary")
        policy = Dropdown(text='Policy')

    @View.nested
    class entities(View):  # noqa
        summary = ParametrizedView.nested(ParametrizedSummaryTable)

    @property
    def is_displayed(self):
        return (
            self.in_ansible_credentials and
            self.title.text == self.context["object"].expected_details_title
        )


class CredentialFormView(CredentialsBaseView):
    name = Input(name="name")
    credential_form = ConditionalSwitchableView(reference="credential_type")

    @credential_form.register("<Choose>", default=True)
    class CredentialFormDefaultView(View):
        pass

    @credential_form.register("Machine")
    class CredentialFormMachineView(View):
        username = Input(locator='.//input[@title="Username for this credential"]')
        password = Input(
            locator='.//input[@title="Password for this credential" and "not @disabled"]'
        )
        private_key = TextInput(
            locator='.//textarea[@title="RSA or DSA private key to be used instead of password"'
            'and "not @disabled"]'
        )
        private_key_phrase = Input(
            locator='.//input[@title="Passphrase to unlock SSH private key if encrypted"'
            'and "not @disabled"]'
        )
        privilage_escalation = BootstrapSelect("{{name}}")
        privilage_escalation_username = Input(
            locator='.//input[@title="Privilege escalation username"]'
        )
        privilage_escalation_password = Input(
            locator='.//input[@title="Password for privilege escalation method"'
            'and "not @disabled"]'
        )

    @credential_form.register("Scm")
    class CredentialFormScmView(View):
        username = Input(locator='.//input[@title="Username for this credential"]')
        password = Input(
            locator='.//input[@title="Password for this credential" and "not @disabled"]'
        )
        private_key = TextInput(
            locator='.//textarea[@title="RSA or DSA private key to be used instead of password"'
            'and "not @disabled"]'
        )
        private_key_phrase = Input(
            locator='.//input[@title="Passphrase to unlock SSH private key if encrypted"'
            'and "not @disabled"]'
        )

    @credential_form.register("Vault")
    class CredentialFormVaultView(View):
        vault_password = Input(
            locator='.//input[@title="Vault password" and "not @disabled"]'
        )

    @credential_form.register("Amazon")
    class CredentialFormAmazonView(View):
        access_key = Input(
            locator='.//input[@title="AWS Access Key for this credential"]'
        )
        secret_key = Input(
            locator='.//input[@title="AWS Secret Key for this credential" and "not @disabled"]'
        )
        sts_token = Input(
            locator='.//input[@title="Security Token Service(STS) Token for this credential"'
            'and "not @disabled"]'
        )

    @credential_form.register("VMware")
    class CredentialFormVMwareView(View):
        username = Input(locator='.//input[@title="Username for this credential"]')
        password = Input(
            locator='.//input[@title="Password for this credential" and "not @disabled"]'
        )
        vcenter_host = Input(
            locator='.//input[@title="The hostname or IP address of the vCenter Host"]'
        )

    @credential_form.register("OpenStack")
    class CredentialFormOpenStackView(View):
        username = Input(
            locator='.//input[@title="The username to use to connect to OpenStack"]'
        )
        password = Input(
            locator='.//input[@title="The password or API'
            ' key to use to connect to OpenStack" and "not @disabled"]'
        )
        authentication_url = Input(
            locator='.//input[@title="The host to authenticate with. '
            'For example, https://openstack.business.com/v2.0"]'
        )
        project = Input(
            locator='.//input[@title="This is the tenant name. This value '
            'is usually the same as the username"]'
        )
        domain = Input(
            locator='.//input[@title="OpenStack domains define administrative '
            'boundaries. It is only needed for Keystone v3 authentication URLs"]'
        )

    @credential_form.register("Red Hat Virtualization")
    class CredentialFormRHVView(View):
        username = Input(locator='.//input[@title="Username for this credential"]')
        password = Input(
            locator='.//input[@title="Password for this credential" and "not @disabled"]'
        )
        host = Input(locator='.//input[@title="The host to authenticate with"]')

    @credential_form.register("Google Compute Engine")
    class CredentialFormGCEView(View):
        service_account = Input(
            locator='.//input[@title="The email address assigned to '
            'the Google Compute Engine service account"]'
        )
        priv_key = TextInput(
            locator='.//textarea[@title="Contents of the PEM file associated with '
            'the service account email"]'
        )
        project = Input(
            locator='.//input[@title="The GCE assigned identification. It is '
            "constructed as two words followed by a three digit number, such as: "
            'squeamish-ossifrage-123"]'
        )

    @credential_form.register("Azure")
    class CredentialFormAzureView(View):
        username = Input(
            locator='.//input[@title="The username to use to connect to the '
            'Microsoft Azure account"]'
        )
        password = Input(
            locator='.//input[@title="The password to use to connect to the '
            'Microsoft Azure account"]'
        )
        subscription_id = Input(
            locator='.//input[@title="The Subscription UUID for the Microsoft Azure account"]'
        )
        tenant_id = Input(
            locator='.//input[@title="The Tenant ID for the Microsoft Azure account"]'
        )
        client_secret = Input(
            locator='.//input[@title="The Client Secret for the Microsoft Azure account"]'
        )
        client_id = Input(
            locator='.//input[@title="The Client ID for the Microsoft Azure account"]'
        )

    @credential_form.register("Network")
    class CredentialFormNetworkView(View):
        username = Input(locator='.//input[@title="Username for this credential"]')
        password = Input(locator='.//input[@title="Password for this credential"]')
        authorize = Input(
            locator='.//input[@title="Whether to use the authorize mechanism"]'
        )
        authorize_password = Input(
            locator='.//input[@title="Password used by the authorize mechanism"]'
        )
        ssh_key = TextInput(
            locator='.//textarea[@title="RSA or DSA private key to be used instead of password"'
            'and "not @disabled"]'
        )
        private_key_phrase = Input(
            locator='.//input[@title="Passphrase to unlock SSH private key if encrypted"'
            'and "not @disabled"]'
        )

    cancel_button = Button("Cancel")


class CredentialAddView(CredentialFormView):
    credential_type = BootstrapSelect("type")
    add_button = Button("Add")

    @property
    def is_displayed(self):
        return (
            self.in_ansible_credentials and
            self.title.text == "Add a new Credential"
        )


class CredentialEditView(CredentialFormView):

    @ParametrizedView.nested
    class input(ParametrizedView):  # noqa
        PARAMETERS = ("title", )
        field_enable = Text(ParametrizedLocator(
            ".//*[(self::input or self::textarea) and "
            "@title={title|quote}]/../../a[text()='Update']"))
        field_disable = Text(ParametrizedLocator(
            ".//*[(self::input or self::textarea) and "
            "@title={title|quote}]/../../a[text()='Cancel']"))

        def toggle(self):
            if self.field_enable.is_displayed:
                self.field_enable.click()
            elif self.field_disable.is_displayed:
                self.field_disable.click()

    credential_type = Text(locator=".//label[normalize-space(.)='Credential type']/../div")
    save_button = Button("Save")
    reset_button = Button("Reset")

    @property
    def is_displayed(self):
        return (
            self.in_ansible_credentials and
            self.title.text == 'Edit a Credential "{}"'.format(self.context["object"].name)
        )

    def before_fill(self, values):
        for name in self.widget_names:
            if name not in values or values[name] is None:
                continue
            widget = getattr(self, name)
            title = self.browser.get_attribute("title", widget)
            try:
                self.input(title).toggle()
            except NoSuchElementException:
                continue


def machine_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "private_key": credentials.get("private_key"),
        "private_key_phrase": credentials.get("private_key_phrase"),
        "privilage_escalation": credentials.get("privilage_escalation"),
        "privilage_escalation_username": credentials.get("privilage_escalation_username"),
        "privilage_escalation_password": credentials.get("privilage_escalation_password"),
    }


def scm_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "private_key": credentials.get("private_key"),
        "private_key_phrase": credentials.get("private_key_phrase")
    }


def vault_credentials(credentials):
    return {
        "vault_password": credentials.get("vault_password")
    }


def amazon_credentials(credentials):
    return {
        "access_key": credentials.get("access_key"),
        "secret_key": credentials.get("secret_key"),
        "sts_token": credentials.get("sts_token"),
    }


def azure_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "subscription_id": credentials.get("subscription_id"),
        "tenant_id": credentials.get("tenant_id"),
        "client_secret": credentials.get("client_secret"),
        "client_id": credentials.get("client_id"),
    }


def network_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "authorize": credentials.get("authorize"),
        "authorize_password": credentials.get("authorize_password"),
        "ssh_key": credentials.get("ssh_key"),
        "private_key_phrase": credentials.get("private_key_phrase"),
    }


def vmware_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "vcenter_host": credentials.get("vcenter_host")
    }


def openstack_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "authentication_url": credentials.get("authentication_url"),
        "project": credentials.get("project"),
        "domain": credentials.get("domain")
    }


def gce_credentials(credentials):
    return {
        "service_account": credentials.get("service_account"),
        "priv_key": credentials.get("priv_key"),
        "project": credentials.get("project")
    }


def rhv_credentials(credentials):
    return {
        "username": credentials.get("username"),
        "password": credentials.get("password"),
        "host": credentials.get("host")
    }


class Credential(BaseEntity, Taggable):
    """A class representing one Embedded Ansible credential in the UI."""

    # TODO - This is one of the only classes that hasn't been converted to attrs
    # The class needs to be reworked and split into multiple subtypes. The kwargs
    # is also problematic for attrs

    def __init__(self, collection, name, credential_type, **credentials):
        super().__init__(collection)
        self.name = name
        self.credential_type = credential_type
        for key, value in credentials.items():
            setattr(self, key, value)

    __repr__ = object.__repr__

    def update(self, updates):
        credential_type_map = {
            "Machine": machine_credentials(updates),
            "Scm": scm_credentials(updates),
            "Vault": vault_credentials(updates),
            "Amazon": amazon_credentials(updates),
            "Azure": azure_credentials(updates),
            "Network": network_credentials(updates),
            "VMware": vmware_credentials(updates),
            "OpenStack": openstack_credentials(updates),
            "Red Hat Virtualization": rhv_credentials(updates),
            "Google Compute Engine": gce_credentials(updates)
        }
        edit_page = navigate_to(self, "Edit")
        changed = edit_page.fill({"name": updates.get("name")})
        form_changed = edit_page.credential_form.fill(credential_type_map[self.credential_type])
        if changed or form_changed:
            edit_page.save_button.click()
        else:
            edit_page.cancel_button.click()
        view = self.create_view(CredentialsListView)
        wait_for(lambda: False, silent_failure=True, timeout=5)
        assert view.is_displayed
        view.flash.assert_no_error()
        if changed or form_changed:
            view.flash.assert_message(
                'Modification of Credential "{}" has been successfully queued.'.format(
                    updates.get("name", self.name)))
        else:
            view.flash.assert_message(
                f'Edit of Credential "{self.name}" was canceled by the user.')

    def delete(self):
        view = navigate_to(self, "Details")
        view.toolbar.configuration.item_select("Remove this Credential from Inventory",
                                               handle_alert=True)
        credentials_list_page = self.create_view(CredentialsListView)
        wait_for(lambda: False, silent_failure=True, timeout=5)
        assert credentials_list_page.is_displayed
        credentials_list_page.flash.assert_success_message(
            f'Deletion of Credential "{self.name}" was successfully initiated.')
        wait_for(
            lambda: not self.exists,
            delay=10,
            fail_func=credentials_list_page.browser.selenium.refresh,
            timeout=300
        )


@attr.s
class CredentialsCollection(BaseCollection):
    """Collection object for the :py:class:`Credential`."""

    ENTITY = Credential

    def create(self, name, credential_type, **credentials):
        add_page = navigate_to(self, "Add")
        credential_type_map = {
            "Machine": machine_credentials(credentials),
            "Scm": scm_credentials(credentials),
            "Vault": vault_credentials(credentials),
            "Amazon": amazon_credentials(credentials),
            "Azure": azure_credentials(credentials),
            "Network": network_credentials(credentials),
            "VMware": vmware_credentials(credentials),
            "OpenStack": openstack_credentials(credentials),
            "Red Hat Virtualization": rhv_credentials(credentials),
            "Google Compute Engine": gce_credentials(credentials)
        }

        add_page.fill({"name": name, "credential_type": credential_type})
        add_page.credential_form.fill(credential_type_map[credential_type])
        add_page.add_button.click()
        credentials_list_page = self.create_view(CredentialsListView)
        # Without this StaleElementReferenceException can be raised
        wait_for(lambda: False, silent_failure=True, timeout=5)
        assert credentials_list_page.is_displayed
        credentials_list_page.flash.assert_success_message(
            f'Add of Credential "{name}" has been successfully queued.')

        credential = self.instantiate(name, credential_type, **credentials)

        wait_for(
            lambda: credential.exists,
            fail_func=credentials_list_page.browser.selenium.refresh,
            delay=5,
            timeout=300)

        return credential


@navigator.register(Server)
class AnsibleCredentials(CFMENavigateStep):
    VIEW = CredentialsListView
    prerequisite = NavigateToSibling("LoggedIn")

    def step(self, *args, **kwargs):
        self.view.navigation.select("Automation", "Ansible", "Credentials")


@navigator.register(Credential)
class Details(CFMENavigateStep):
    VIEW = CredentialDetailsView
    prerequisite = NavigateToAttribute("appliance.server", "AnsibleCredentials")

    def step(self, *args, **kwargs):
        credentials = self.prerequisite_view.credentials
        try:
            for row in credentials:
                if row["Name"].text == self.obj.name:
                    row["Name"].click()
                    break
            else:
                raise ItemNotFound
        except NoSuchElementException:
            raise ItemNotFound


@navigator.register(CredentialsCollection)
class Add(CFMENavigateStep):
    VIEW = CredentialAddView
    prerequisite = NavigateToAttribute("appliance.server", "AnsibleCredentials")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Add New Credential")


@navigator.register(Credential)
class Edit(CFMENavigateStep):
    VIEW = CredentialEditView
    prerequisite = NavigateToSibling("Details")

    def step(self, *args, **kwargs):
        self.prerequisite_view.toolbar.configuration.item_select("Edit this Credential")


@navigator.register(Credential, 'EditTags')
class EditTagsFromListCollection(CFMENavigateStep):
    VIEW = TagPageView

    prerequisite = NavigateToAttribute("appliance.server", "AnsibleCredentials")

    def step(self, *args, **kwargs):
        try:
            row = self.prerequisite_view.paginator.find_row_on_pages(
                table=self.prerequisite_view.credentials,
                name=self.obj.name)
            row[0].check()
        except NoSuchElementException:
            raise ItemNotFound('Could not locate ansible credential table row with name {}'
                               .format(self.obj.name))
        self.prerequisite_view.toolbar.policy.item_select('Edit Tags')
