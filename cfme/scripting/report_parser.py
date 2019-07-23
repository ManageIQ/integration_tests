"""Script to parse test reports."""
import json

import click

from cfme.utils.log import add_stdout_handler
from cfme.utils.log import logger

# Log to stdout too
add_stdout_handler(logger)


class ReportParser:
    def __init__(self, report_path, report_format='json', report_dict=None, *args, **kwargs):
        self.report_path = report_path
        self.report_format = report_format  # for now only support json
        self.report_dict = self._pull_in_report()

    def _pull_in_report(self):
        if self.report_format == 'json':
            try:
                with open(self.report_path) as json_file:
                    return json.load(json_file)
            except IOError:
                logger.error("File {} does not exist".format(self.report_path))
                raise

    def parse_report_per_user(self, filter_by='failed', user=''):
        tests = self.report_dict['tests']
        assignee_wise_results = {}
        for test_case in tests:
            result = tests[test_case]['statuses']['overall']
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
@click.option("--report-file", help="Path to the file with json data")
@click.option("--email-users", type=bool, help="If set to True, users receive email with the report"
    " Default False.", default=False)
@click.option("--user", help="Set this if you want to filter the report for a specific user",
    default='')
@click.option("--filter-by", type=click.Choice(['passed', 'failed', 'skipped']),
    help="Defaults to 'failed'", default='failed')
def test_results_per_assignee(report_file, email_users, user, filter_by):
    rp = ReportParser(report_file)
    print(rp.parse_report_per_user(filter_by, user))
