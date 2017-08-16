from widgetastic.widget import Checkbox, Input, Table, Text, View
from widgetastic_manageiq import FileInput, SummaryForm, SummaryTable
from widgetastic_patternfly import (
    BootstrapSelect as VanillasBootstrapSelect,
    BootstrapSwitch,
    Button,
    Tab
)
from utils.appliance import Navigatable
from utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to
from . import ServicesCatalogView


class BootstrapSelect(VanillaBootstrapSelect):
    ROOT = ParametrizedLocator('.//select[normalize-space(@name)={@id|quote}]/..')


class AnsibleCatalogItemForm(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    name = Input("name")
    description = Input("description")
    display_in_catalog = BootstrapSwitch(name="display")
    catalog = BootstrapSelect("catalog_id")

    @View.nested
    class provisioning(Tab):  # noqa
        repository = BootstrapSelect("provisioning_repository_id")
        playbook = BootstrapSelect("provisioning_playbook_id")
        machine_credential = BootstrapSelect("provisioning_machine_credential_id")
        cloud_type = BootstrapSelect("provisioning_cloud_type")
        hosts = Input("provisioning_inventory")
        escalate_privilege = BootstrapSwitch(name="provisioning_become_enabled")
        verbosity = BootstrapSelect("provisioning_verbosity")
        use_exisiting = Checkbox(name="213")
        create_new = Checkbox(name="214")
        provisioning_dialog_id = BootstrapSelect(name="provisioning_dialog_id")
        provisioning_dialog_name = Input(name="vm.provisioning_dialog_name")

    @View.nested
    class retirement(Tab):  # noqa
        # TODO Somehow need to handle a modal window
        copy_from_provisioning = Button("Copy from provisioning")
        repository = BootstrapSelect("retirement_repository_id")
        playbook = BootstrapSelect("provisioning_playbook_id")
        machine_credential = BootstrapSelect("provisioning_machine_credential_id")
        cloud_type = BootstrapSelect("provisioning_cloud_type")
        hosts = Input("retirement_inventory")
        escalate_privilege = BootstrapSwitch(name="provisioning_become_enabled")
        verbosity = BootstrapSelect("retirement_verbosity")
        remove_resources = BootstrapSelect("vm.catalogItemModel.retirement_remove_resources")

    cancel = Button("Cancel")

class AddAnsibleCatalogItemView(AnsibleCatalogItemForm):
    add = Button("Add")


class EditAnsibleCatalogItemView(AnsibleCatalogItemForm):
    save = Button("Save")
    reset = Button("Reset")


class DetailsAnsibleCatalogItemView(ServicesCatalogView):
    title = Text(".//span[@id='explorer_title_text']")
    basic_information = SummaryForm("Basic Information")
    custom_image = FileInput("upload_image")
    upload = Button("Upload")
    smart_management = SummaryTable("Smart Management")

    @View.nested
    class provisioning(Tab):  # noqa
        provisioning_info = SummaryForm("Provisioning Info")
        variables_and_default_values = Table(".//div[@id='provisioning']//table")

    @View.nested
    class retirement(Tab):  # noqa
        retirement_info = SummaryForm("Retirement Info")
        variables_and_default_values = Table(".//div[@id='retirement']//table")

    @property
    def is_displayed(self):
        pass
    

class AnsiblePlaybookCatalogItem(Navigatable):
    pass
