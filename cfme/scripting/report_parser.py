"""Script to parse test reports."""
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import click
import yaml

from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger

# Log to stdout too
add_stdout_handler(logger)


class ReportParser:
    def __init__(self, report_path, report_format='json', report_dict=None, *args, **kwargs):
        self.report_path = report_path
        self.report_format = report_format  # for now only support json
        self.report_dict = report_dict or self._pull_in_report()

    def _pull_in_report(self):
        if self.report_format == 'json':
            try:
                with open(self.report_path) as json_file:
                    return json.load(json_file)
            except IOError:
                logger.exception("File {} does not exist".format(self.report_path))
                raise

    def parse_report_per_user(self, filter_by='failed', user=''):
        tests = self.report_dict['tests']
        assignee_wise_results = {}
        for test_case in tests:
            try:
                result = tests[test_case]['statuses']['overall']
            except KeyError:
                # continue loop if any test is missing the statuses/overall
                continue
            # if user='' it will fetch for all users
            if (result == filter_by and user in tests[test_case]['assignee']):
                try:
                    assignee_wise_results[tests[test_case]['assignee']].update(
                        {test_case: result})
                except KeyError:
                    assignee_wise_results[tests[test_case]['assignee']] = (
                        {test_case: result})
        return assignee_wise_results


@click.group("blame", help="Functions for generating reports on Tests grouped by user")
def main():
    pass


@main.command("test-report", help="Returns a Dictionary containing failed test cases per user")
@click.option("--report-file", help="Path to the file with json data", required=True)
@click.option("--email-config-yaml", help="The path to your email configuration file,"
    " e.g. 'report_parser_email_conf.yaml'",
    type=click.Path())
@click.option("--user", help="Set this if you want to filter the report for a specific user",
    default='')
@click.option("--filter-by", type=click.Choice(['passed', 'failed', 'skipped']),
    help="Defaults to 'failed'", default='failed')
def test_results_per_assignee(report_file, email_config_yaml, user, filter_by):
    rp = ReportParser(report_file)
    test_report_dict = rp.parse_report_per_user(filter_by, user)
    # user is required before following routine would execute, else no email is sent
    if test_report_dict and email_config_yaml:
        try:
            with open(email_config_yaml, "r") as config_file:
                email_config = yaml.safe_load(config_file)
        except IOError:
            logger.exception("Please provide valid file path for --email-config-yaml")
        server = smtplib.SMTP(
            host=email_config['email_host'],
            port=email_config['email_port']
        )
        email_msg = MIMEMultipart()
        try:
            email_msg['From'] = email_config['from_addr']
            email_msg['To'] = '{}@redhat.com'.format(user if user else
                email_config['default_to_addr'])
            email_msg['Subject'] = email_config['email_subject']
            if user:
                pretty_test_report_dict = '\n'.join(['{:<15} {:<10}'.format(k, v)
                                            for k, v in test_report_dict[user].items()])
            else:
                pretty_test_report_dict = ''
                for u in test_report_dict.keys():
                    pretty_test_report_dict += ''.join(['{:<5} {:<15} {:<10}\n'.format(u, k, v)
                                                for k, v in test_report_dict[u].items()])
            email_msg.attach(
                MIMEText(email_config['email_template']
                .format(user if user else email_config['default_to_addr'],
                    pretty_test_report_dict))
            )
        except KeyError:
            logger.exception("Make sure email_config_yaml has all the required keys,"
                " as shown in template")
        try:
            server.sendmail(from_addr=email_config['from_addr'],
                to_addrs='{}@redhat.com'.format(user if user else email_config['default_to_addr']),
                msg=email_msg.as_string())
        except smtplib.SMTPRecipientsRefused:
            logger.exception("Server refused to accept the email."
                " Receipient address might be incorrect")
