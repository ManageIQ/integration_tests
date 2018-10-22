# Common stuff for custom button testing

from widgetastic.widget import View, Text, TextInput
from widgetastic_patternfly import Button


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
