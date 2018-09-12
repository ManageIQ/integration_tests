# Common stuff for custom button testing


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


def log_request_check(appliance, initial_count, expected_count):
    """ Method for checking expected request count in automation log

    Args:
        appliance: an appliance for ssh
        initial_count: initial request count available in automation log
        expected_count: expected request count in automation log
    """
    diff = check_log_requests_count(appliance=appliance) - initial_count
    return diff == expected_count
