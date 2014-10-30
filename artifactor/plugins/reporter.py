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
from copy import deepcopy
from jinja2 import Environment, FileSystemLoader
from utils.path import template_path
import math
from operator import itemgetter
import os
import shutil
import time
import datetime


_tests_tpl = {
    '_sub': {},
    '_stats': {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'error': 0,
        'xpassed': 0,
        'xfailed': 0
    },
    '_duration': 0
}


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
    def start_test(self, test_location, test_name, slaveid):
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'start_time': time.time(), 'slaveid': slaveid}}}

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, test_location, test_name, slaveid):
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'finish_time': time.time(), 'slaveid': slaveid}}}

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

        # Iterate through the tests and process the counts and durations
        for test_name, test in artifacts.iteritems():
            if not test.get('statuses', None):
                continue
            overall_status = None

            # Handle some logic for when to count certain tests as which state
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

            # Set the overall status and then process duration
            test['statuses']['overall'] = overall_status
            test_data = {'name': test_name, 'outcomes': test['statuses'],
                         'slaveid': test.get('slaveid', "Unknown")}

            if test.get('start_time', None):
                if test.get('finish_time', None):
                    test_data['in_progress'] = False
                    test_data['duration'] = test['finish_time'] - test['start_time']
                else:
                    test_data['duration'] = time.time() - test['start_time']
                    test_data['in_progress'] = True

            # Set up destinations for the files
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
                    elif "function" in filename:
                        test_data['function'] = filename.replace(log_dir, "")
                    elif "emails.html" in filename:
                        test_data['emails'] = filename.replace(log_dir, "")
                    elif "events.html" in filename:
                        test_data['event_testing'] = filename.replace(log_dir, "")
                if "merkyl" in ident:
                    test_data['merkyl'] = [f.replace(log_dir, "")
                                           for f in test['files']['merkyl']]
            template_data['tests'].append(test_data)
        template_data['counts'] = counts

        # Create the tree dict that is used for js tree
        # Note template_data['tests'] != tests
        tests = deepcopy(_tests_tpl)
        tests['_sub']['tests'] = deepcopy(_tests_tpl)

        for test in template_data['tests']:
            self.build_dict(test['name'].replace('cfme/', ''), tests, test)

        template_data['ndata'] = self.build_li(tests)

        # Sort the test output and if necessary discard tests that have passed
        template_data['tests'] = sorted(template_data['tests'], key=itemgetter('name'))
        if self.only_failed:
            template_data['tests'] = [x for x in template_data['tests']
                                  if x['outcomes']['overall'] not in ['skipped', 'passed']]

        # Render the report
        data = template_env.get_template('test_report.html').render(**template_data)
        with open(os.path.join(log_dir, 'report.html'), "w") as f:
            f.write(data)
        try:
            shutil.copytree(template_path.join('dist').strpath, os.path.join(log_dir, 'dist'))
        except OSError:
            pass

    def build_dict(self, path, container, contents):
        """
        Build a hierarchical dictionary including information about the stats at each level
        and the duration.
        """
        segs = path.split('/')
        head = segs[0]
        end = segs[1:]

        # If we are at the end node, ie a test.
        if not end:
            container['_sub'][head] = contents
            container['_stats'][contents['outcomes']['overall']] += 1
            container['_duration'] += contents['duration']
        # If we are in a module.
        else:
            if head not in container['_sub']:
                container['_sub'][head] = deepcopy(_tests_tpl)
            # Call again to recurse down the tree.
            self.build_dict('/'.join(end), container['_sub'][head], contents)
            container['_stats'][contents['outcomes']['overall']] += 1
            container['_duration'] += contents['duration']

    def build_li(self, lev):
        """
        Build up the actual HTML tree from the dict from build_dict
        """
        bimdict = {'passed': 'success',
                   'failed': 'warning',
                   'error': 'danger',
                   'skipped': 'primary',
                   'xpassed': 'danger',
                   'xfailed': 'success'}
        list_string = '<ul>\n'
        for k, v in lev['_sub'].iteritems():

            # If 'name' is an attribute then we are looking at a test (leaf).
            if 'name' in v:
                pretty_time = str(datetime.timedelta(seconds=math.ceil(v['duration'])))
                teststring = '<span name="mod_lev" class="label label-primary">T</span>'
                label = '<span class="label label-{}">{}</span>'.format(
                    bimdict[v['outcomes']['overall']], v['outcomes']['overall'].upper())
                link = ('<a href="#{}">{} {} {} '
                        '<span style="color:#888888"><em>[{}]</em></span></a>').format(
                    v['name'], os.path.split(v['name'])[1], teststring, label, pretty_time)
                list_string += '<li>{}</li>\n'.format(link)

            # If there is a '_sub' attribute then we know we have other modules to go.
            elif '_sub' in v:
                percenstring = ""
                bmax = 0
                for kek, val in v['_stats'].iteritems():
                    if kek not in ('skipped', 'xfailed'):
                        bmax += val
                # If there were any NON skipped tests, we now calculate the percentage which
                # passed.
                if bmax:
                    percen = "{:.2f}".format(float(v['_stats']['passed']) / float(bmax) * 100)
                    if float(percen) == 100.0:
                        level = 'passed'
                    elif float(percen) > 80.0:
                        level = 'failed'
                    else:
                        level = 'error'
                    percenstring = '<span name="blab" class="label label-{}">{}%</span>'.format(
                        bimdict[level], percen)
                modstring = '<span name="mod_lev" class="label label-primary">M</span>'
                pretty_time = str(datetime.timedelta(seconds=math.ceil(v['_duration'])))
                list_string += ('<li>{} {}<span>&nbsp;</span>'
                                '{}{}<span style="color:#888888">&nbsp;<em>[{}]'
                                '</em></span></li>\n').format(k,
                                                              modstring,
                                                              str(percenstring),
                                                              self.build_li(v),
                                                              pretty_time)
        list_string += '</ul>\n'
        return list_string
