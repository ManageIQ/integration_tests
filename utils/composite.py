import json
import socket
from collections import OrderedDict
from Queue import Queue
from threading import Lock, Thread

from paramiko import SSHException
from progress.bar import IncrementalBar as Bar
from py.path import local
from scp import SCPClient, SCPException

from artifactor.plugins import reporter
from artifactor.plugins.post_result import test_counts
from utils.conf import composite, credentials
from utils import trackerbot
from utils.ssh import SSHClient

lock = Lock()


def _queue_worker(rc):
    # multithreaded file puller, takes tuples of remote, local, item, items_done
    # pulls the files and then updates the progress meter

    jenkins_host = composite['jenkins_host']
    client = rc.ssh_client
    client.connect(jenkins_host, username=credentials['jenkins-result']['username'],
            password=credentials['jenkins-result']['password'],
            timeout=10,
            allow_agent=False,
            look_for_keys=False,
            gss_auth=False)
    scp = None

    while True:
        source, destination, item, items_done = rc._queue.get()
        destination = local(destination)
        destination_dir = local(destination.dirname)
        destination_dir.ensure(dir=True)
        if not destination.check():
            if scp is None:
                scp = SCPClient(client.get_transport())
            try:
                scp.get(source, destination.strpath)
            except SCPException:
                # remote destination didn't exist
                pass
            except (SSHException, socket.timeout):
                # SSH blew up :(
                rc._queue.put((source, destination, item, items_done))
                rc._queue.task_done()
                continue
        rc._progress_update(item, items_done)
        rc._queue.task_done()


class ReportCompile(object):
    def __init__(self, job_name, template, **kwargs):
        self.job_name = job_name
        self.template = template
        self.no_artifacts = kwargs.get('no_artifacts', True)
        self.num_builds = int(kwargs.get('num_builds', composite['num_builds']))
        self.minimum_build = int(kwargs.get('minimum_build', composite['min_build']))
        self.exclude_builds = [int(xb) for xb in kwargs.get('exclude_builds', [])]
        try:
            self.work_dir = local(kwargs.get('work_dir', composite['work_dir']))
            self.work_dir.ensure(dir=True)
        except KeyError:
            self.work_dir = local.mkdtemp()
            print 'Writing composite report to {}'.format(self.work_dir.strpath)
        self._progress = None
        self._queue = Queue()
        num_workers = 4
        for __ in xrange(num_workers):
            worker = Thread(target=_queue_worker, args=(self,))
            worker.daemon = True
            worker.start()

    @property
    def ssh_client(self):
        c = SSHClient()
        return c

    @staticmethod
    def _best_result(*results):
        # results should be a list of (result_id, result_value) tuples
        # result ranking, best to worst
        results_ranking = ('passed', 'xfailed', 'failed', 'xpassed', 'skipped', 'error')
        # Go through all the results, returning the best outcome based on results_ranking
        for result in results_ranking:
            for result_id, result_value in reversed(sorted(results, key=lambda r: r[0])):
                if result_value == result:
                    return (result_id, result_value)

    @staticmethod
    def _streak(*results):
        sorted_results = sorted(results, key=lambda r: r[0])
        # the value of the highest numbered (and therefore more recent) build
        latest_result = sorted_results[-1][1]
        streak = 0
        for __, result_value in reversed(sorted_results):
            if result_value == latest_result:
                streak += 1
            else:
                break
        return {'latest_result': latest_result, 'count': streak}

    def _progress_update(self, item, items_done):
        if self._progress is None:
            self._progress = Bar()
            self._progress.message = '%(index)d/%(max)d'
            self._progress.suffix = ''
        if item:
            items_done[item] = True
        self._progress.max = len(items_done)
        self._progress.index = len(filter(None, items_done.values()))
        with lock:
            try:
                self._progress.update()
            except ZeroDivisionError:
                pass

    def _progress_finish(self):
        self._progress.finish()
        self._progress = None

    def compile(self):
        return self.composite_report()

    def build_numbers(self):
        api = trackerbot.api()
        builds = trackerbot.depaginate(api,
            api.build.get(job_name=self.job_name, template=self.template)
        )
        build_numbers = []
        # XXX relying on trackerbot giving us the most recent builds first, should be explicit
        for build in builds.get('objects', []):
            if (build['number'] not in self.exclude_builds
                    and build['number'] >= self.minimum_build):
                build_numbers.append(build['number'])
                if self.num_builds and len(build_numbers) == self.num_builds:
                    break
        if build_numbers:
            print 'Pulling reports from builds {}'.format(
                ', '.join([str(n) for n in build_numbers]))
        return build_numbers

    def template_log_dirs(self):
        log_dir_tpl = composite['log_dir_tpl']
        log_dirs = []
        for build_number in self.build_numbers():
            log_dirs.append((build_number, log_dir_tpl.format(self.job_name, build_number)))
        return log_dirs

    def test_reports(self):
        print 'Collecting test reports to determine best build nodes'
        log_dirs = self.template_log_dirs()
        reports = {}
        c = self.ssh_client
        jenkins_host = composite['jenkins_host']
        c.connect(jenkins_host, username=credentials['jenkins-result']['username'],
            password=credentials['jenkins-result']['password'],
            timeout=10,
            allow_agent=False,
            look_for_keys=False,
            gss_auth=False)
        builds_done = {}
        self._progress_update(None, builds_done)
        for build_number, log_dir in log_dirs:
            build_work_dir = local(self.work_dir.join(str(build_number)))
            build_work_dir.ensure(dir=True)
            _remote = local(log_dir).join('test-report.json').strpath
            _local = build_work_dir.join('test-report.json').strpath
            builds_done[build_number] = False
            self._progress_update(None, builds_done)
            self._queue.put((_remote, _local, build_number, builds_done))
        self._queue.join()
        self._progress_finish()
        for build_number, __ in log_dirs:
            build_work_dir = local(self.work_dir.join(str(build_number)))
            for path in build_work_dir.visit('*/test-report.json'):
                try:
                    report = json.load(path.open())
                    reports[build_number] = report
                except:
                    # invalid json, skip this report
                    pass
        return reports

    def composite_status(self, reports=None):
        jenkins_host = composite['jenkins_host']
        reports = reports or self.test_reports()
        results = {}
        # results dict structure:
        # {
        #   nodeid: {
        #     'build_results': {build_id_1: build_id_1_result, build_id_2: ...}
        #     'best_result': (best_build_id, best_build_result)
        #     'result_url': http://jenkins/path/to/build
        #     'streak': (latest_build_result, number_of_results_in_a_row)
        #   },
        #   nodeid: {
        #     ...
        #   }
        # }
        for build_number, report in reports:
            for nodeid, nodedata in report.get('tests', {}).items():
                try:
                    # Try to pull the build statuses, skip the node if we can't
                    node_results_temp = nodedata['statuses']['overall']
                    node_results = results.setdefault(nodeid, {'build_results': {}})
                    node_results['build_results'][build_number] = node_results_temp
                except KeyError:
                    continue
        for nodeid, nodedata in results.items():
            node_results = nodedata['build_results'].items()
            nodedata['best_result'] = self._best_result(*node_results)
            nodedata['result_url'] = 'https://{}/job/{}/{}/'.format(
                jenkins_host, self.job_name, nodedata['best_result'][0]
            )
            nodedata['streak'] = self._streak(*node_results)
            test_counts[nodedata['best_result'][1]] += 1
        return results

    def composite_report(self):
        reports = self.test_reports()
        composite_status = self.composite_status(reports.iteritems())
        composite_report = {
            'test_counts': test_counts,
            'tests': OrderedDict()
        }

        print 'Collecting artifacts from best build nodes'
        # tracking dict for file pull progress
        remotes_done = {}
        self._progress_update(None, remotes_done)
        for nodeid, nodedata in sorted(composite_status.items(),
                key=lambda s: s[1]['streak']['count'], reverse=True):
            best_build_number = nodedata['best_result'][0]
            best_build_test = reports[best_build_number]['tests'][nodeid]
            composite_report['tests'][nodeid] = best_build_test
            composite_report['tests'][nodeid]['composite'] = nodedata
            reports[best_build_number]['tests'][nodeid]['files'] = []
        # wait for all the files to arrive before building the report
        self._queue.join()
        self._progress_finish()
        json.dump(composite_report, self.work_dir.join('composite-report.json').open('w'),
            indent=1)
        try:
            passing_percent = (100. * (test_counts['passed'] + test_counts['skipped']
                + test_counts['xfailed'])) / sum(test_counts.values())
            print 'Passing percent:', passing_percent
            # XXX: Terrible artifactor spoofing happens here.
            print 'Running artifactor reports'
            r = reporter.ReporterBase()
            reports_done = {'composite': False, 'provider': False}
            self._progress_update(None, reports_done)
            r._run_report(composite_report['tests'], self.work_dir.strpath)
            self._progress_update('composite', reports_done)
            r._run_provider_report(composite_report['tests'], self.work_dir.strpath)
            self._progress_update('provider', reports_done)
            self._progress_finish()
        except ZeroDivisionError:
            print 'No tests collected from test reports (?!)'
        return composite_report

    def _translate_artifacts_path(self, artifact_path, build_number):
        preamble = composite['preamble'].format(self.job_name)
        replacement = composite['replacement'].format(self.job_name, build_number)
        artifact_remote = artifact_path.replace(preamble, replacement)
        artifact_local = self.work_dir.join(str(build_number), artifact_path[len(preamble):])
        try:
            assert artifact_remote.startswith(composite['remote_sw'])
            assert artifact_local.strpath.startswith(self.work_dir.strpath)
        except AssertionError:
            print 'wat?'
            print 'path', artifact_path
            print 'remote', artifact_remote
            print 'local', artifact_local.strpath
        return artifact_remote, artifact_local.strpath
