# Common stuff for custom button testing
from widgetastic.widget import ParametrizedLocator
from widgetastic.widget import ParametrizedView
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import BootstrapSelect
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown


OBJ_TYPE = [
    "AZONE",
    "CLOUD_NETWORK",
    "CLOUD_OBJECT_STORE_CONTAINER",
    "CLOUD_SUBNET",
    "CLOUD_TENANT",
    "CLOUD_VOLUME",
    "CLUSTERS",
    "CONTAINER_IMAGES",
    "CONTAINER_NODES",
    "CONTAINER_PODS",
    "CONTAINER_PROJECTS",
    "CONTAINER_TEMPLATES",
    "CONTAINER_VOLUMES",
    "DATASTORES",
    "GROUP",
    "USER",
    "GENERIC",
    "HOSTS",
    "LOAD_BALANCER",
    "ROUTER",
    "ORCHESTRATION_STACK",
    "PROVIDER",
    "SECURITY_GROUP",
    "SERVICE",
    "SWITCH",
    "TENANT",
    "TEMPLATE_IMAGE",
    "VM_INSTANCE",
]

CLASS_MAP = {
    "AZONE": {"ui": "Availability Zone", "rest": "AvailabilityZone"},
    "CLOUD_NETWORK": {"ui": "Cloud Network", "rest": "CloudNetwork"},
    "CLOUD_OBJECT_STORE_CONTAINER": {
        "ui": "Cloud Object Store Container",
        "rest": "CloudObjectStoreContainer",
    },
    "CLOUD_SUBNET": {"ui": "Cloud Subnet", "rest": "CloudSubnet"},
    "CLOUD_TENANT": {"ui": "Cloud Tenant", "rest": "CloudTenant"},
    "CLOUD_VOLUME": {"ui": "Cloud Volume", "rest": "CloudVolume"},
    "CLUSTERS": {"ui": "Cluster / Deployment Role", "rest": "EmsCluster"},
    "CONTAINER_IMAGES": {"ui": "Container Image", "rest": "ContainerImage"},
    "CONTAINER_NODES": {"ui": "Container Node", "rest": "ContainerNode"},
    "CONTAINER_PODS": {"ui": "Container Pod", "rest": "ContainerGroup"},
    "CONTAINER_PROJECTS": {"ui": "Container Project", "rest": "ContainerProject"},
    "CONTAINER_TEMPLATES": {"ui": "Container Template", "rest": "ContainerTemplate"},
    "CONTAINER_VOLUMES": {"ui": "Container Volume", "rest": "ContainerVolume"},
    "DATASTORES": {"ui": "Datastore", "rest": "Storage"},
    "GROUP": {"ui": "Group", "rest": "MiqGroup"},
    "USER": {"ui": "User", "rest": "User"},
    "GENERIC": {"ui": "Generic Object", "rest": "GenericObject"},
    "HOSTS": {"ui": "Host / Node", "rest": "Host"},
    "LOAD_BALANCER": {"ui": "Load Balancer", "rest": "LoadBalancer"},
    "ROUTER": {"ui": "Network Router", "rest": "NetworkRouter"},
    "ORCHESTRATION_STACK": {"ui": "Orchestration Stack", "rest": "OrchestrationStack"},
    "PROVIDER": {"ui": "Provider", "rest": "ExtManagementSystem"},
    "SECURITY_GROUP": {"ui": "Security Group", "rest": "SecurityGroup"},
    "SERVICE": {"ui": "Service", "rest": "Service"},
    "SWITCH": {"ui": "Virtual Infra Switch", "rest": "Switch"},
    "TENANT": {"ui": "Tenant", "rest": "Tenant"},
    "TEMPLATE_IMAGE": {"ui": "VM Template and Image", "rest": "MiqTemplate"},
    "VM_INSTANCE": {"ui": "VM and Instance", "rest": "Vm"},
}


def check_log_requests_count(appliance, parse_str=None):
    """ Method for checking number of requests count in automation log

    Args:
        appliance: an appliance for ssh
        parse_str: string check-in automation log

    Return: requests string count
    """
    if not parse_str:
        parse_str = "Attributes - Begin"

    count = appliance.ssh_client.run_command(
        f"grep -c -w '{parse_str}' /var/www/miq/vmdb/log/automation.log"
    )
    return int(count.output)


def log_request_check(appliance, expected_count):
    """ Method for checking expected request count in automation log

    Args:
        appliance: an appliance for ssh
        expected_count: expected request count in automation log
    """
    return check_log_requests_count(appliance=appliance) == expected_count


class TextInputDialogView(View):
    """ This is view comes on different custom button objects for dialog execution"""

    title = Text("#explorer_title_text")
    service_name = TextInput(id="service_name")
    submit = Button("Submit")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        # This is only for wait for view
        return self.submit.is_displayed and self.service_name.is_displayed


class TextInputAutomateView(View):
    """This is view comes on clicking custom button"""

    title = Text("#explorer_title_text")
    text_box1 = TextInput(id="text_box_1")
    text_box2 = TextInput(id="text_box_2")
    submit = Button("Submit")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return (self.submit.is_displayed and
                self.text_box1.is_displayed and
                self.text_box2.is_displayed)


class CredsHostsDialogView(View):
    """This view for custom button default ansible playbook dialog"""

    machine_credential = BootstrapSelect(locator=".//select[@id='credential']//parent::div")
    hosts = TextInput(id="hosts")

    submit = Button("Submit")
    cancel = Button("Cancel")

    @property
    def is_displayed(self):
        return self.submit.is_displayed and self.machine_credential.is_displayed


class TextInputDialogSSUIView(TextInputDialogView):
    """ This is view comes on SSUI custom button dialog execution"""

    submit = Button("Submit Request")


class DropdownDialogView(ParametrizedView):
    """ This is custom view for custom button dropdown dialog execution"""

    title = Text("#explorer_title_text")

    class service_name(ParametrizedView):  # noqa
        PARAMETERS = ("dialog_id",)
        dropdown = BootstrapSelect(
            locator=ParametrizedLocator("//select[@id={dialog_id|quote}]/..")
        )

    submit = Button("Submit")
    submit_request = Button("Submit Request")
    cancel = Button("Cancel")


class CustomButtonSSUIDropdwon(Dropdown):
    """This is workaround for custom button Dropdown in SSUI item_enabled method"""

    def item_enabled(self, item):
        self._verify_enabled()
        el = self.item_element(item)
        return "disabled" not in self.browser.classes(el)
