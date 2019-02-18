# Common stuff for custom button testing
from widgetastic.widget import Text
from widgetastic.widget import TextInput
from widgetastic.widget import View
from widgetastic_patternfly import Button
from widgetastic_patternfly import Dropdown


OBJ_TYPE_59 = [
    "CLOUD_TENANT",
    "CLOUD_VOLUME",
    "CLUSTERS",
    "CONTAINER_NODES",
    "CONTAINER_PROJECTS",
    "DATASTORES",
    "GENERIC",
    "HOSTS",
    "PROVIDER",
    "SERVICE",
    "TEMPLATE_IMAGE",
    "VM_INSTANCE",
]

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
        "grep -c -w '{parse_str}' /var/www/miq/vmdb/log/automation.log".format(parse_str=parse_str)
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


class CustomButtonSSUIDropdwon(Dropdown):
    """This is workaround for custom button Dropdown in SSUI item_enabled method"""

    def item_enabled(self, item):
        self._verify_enabled()
        el = self.item_element(item)
        return 'disabled' not in self.browser.classes(el)
