""" Reporter plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    reuse_dir: True
    plugins:
        reporter:
            enabled: True
            plugin: reporter
            only_failed: False #Only show faled tests in the report
"""

from artifactor.utils import ArtifactorBasePlugin
from jinja2 import Environment, FileSystemLoader
from utils.path import template_path
import os
import time


class Reporter(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('report_test', self.report_test)
        self.register_plugin_hook('finish_session', self.run_report)
        self.register_plugin_hook('build_report', self.run_report)
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)

    def configure(self):
        self.only_failed = self.data.get('only_failed', False)
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def start_test(self, test_location, test_name):
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'start_time': time.time()}}}

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, test_location, test_name):
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'finish_time': time.time()}}}

    @ArtifactorBasePlugin.check_configured
    def report_test(self, test_location, test_name, test_xfail, test_when, test_outcome):
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'statuses': {
            test_when: (test_outcome, test_xfail)}}}}

    @ArtifactorBasePlugin.check_configured
    def run_report(self, artifacts, log_dir):
        template_env = Environment(
            loader=FileSystemLoader(template_path.strpath)
        )
        template_data = {'tests': []}
        log_dir += "/"
        counts = {'passed': 0, 'failed': 0, 'skipped': 0, 'error': 0, 'xfailed': 0, 'xpassed': 0}
        for test_name, test in artifacts.iteritems():
            if not test.get('statuses', None):
                continue
            overall_status = None
            for when, status in test['statuses'].iteritems():
                if when == "call" and status[1] and status[0] == "skipped":
                    counts['xfailed'] += 1
                    overall_status = "xfailed"
                    break
                elif when == "call" and status[1] and status[0] == "failed":
                    counts['xpassed'] += 1
                    overall_status = "xpassed"
                    break
                elif (when == "setup" or when == "teardown") and status[0] == "failed":
                    counts['error'] += 1
                    overall_status = "error"
                    break
                elif status[0] == "skipped":
                    counts['skipped'] += 1
                    overall_status = "skipped"
                    break
                elif when == "call" and status[0] == 'failed':
                    counts['failed'] += 1
                    overall_status = "failed"
                    break
            else:
                counts['passed'] += 1
                overall_status = "passed"
                if self.only_failed:
                    continue
            test['statuses']['overall'] = overall_status
            test_data = {'name': test_name, 'outcomes': test['statuses']}
            if test.get('start_time', None):
                if test.get('finish_time', None):
                    test_data['in_progress'] = False
                    test_data['duration'] = test['finish_time'] - test['start_time']
                else:
                    test_data['duration'] = time.time() - test['start_time']
                    test_data['in_progress'] = True
            for ident in test.get('files', []):
                for filename in test['files'].get(ident, []):
                    if "screenshot" in filename:
                        test_data['screenshot'] = filename.replace(log_dir, "")
                    elif "short-traceback" in filename:
                        test_data['short_tb'] = open(filename).read()
                    elif "traceback" in filename:
                        test_data['full_tb'] = filename.replace(log_dir, "")
                    elif "video" in filename:
                        test_data['video'] = filename.replace(log_dir, "")
                    elif "cfme.log" in filename:
                        test_data['cfme'] = filename.replace(log_dir, "")
                if "merkyl" in ident:
                    test_data['merkyl'] = [f.replace(log_dir, "")
                                           for f in test['files']['merkyl']]
            template_data['tests'].append(test_data)
        template_data['counts'] = counts
        data = template_env.get_template('test_report.html').render(**template_data)
        with open(os.path.join(log_dir, 'report.html'), "w") as f:
            f.write(data)
