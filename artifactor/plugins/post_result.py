""" Jenkins result plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    reuse_dir: True
    plugins:
        post-result:
            enabled: True
            plugin: post_result
"""
from collections import defaultdict

from artifactor import ArtifactorBasePlugin

from utils.path import log_path

# preseed the normal statuses, but let defaultdict handle
# any unexpected statuses, which should probably never happen

test_report = log_path.join('test-report.json')
test_counts = defaultdict(int, {
    'passed': 0,
    'failed': 0,
    'skipped': 0,
    'error': 0,
    'xpassed': 0,
    'xfailed': 0
})


class PostResult(ArtifactorBasePlugin):
    def plugin_initialize(self):
        self.register_plugin_hook('finish_session', self.post_result)
        test_report.check() and test_report.remove()

    def configure(self):
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def post_result(self, artifacts, log_dir):
        report = {}
        report['tests'] = artifacts

        def _inc_test_count(test):
            error = ""
            if 'statuses' in test:
                test_counts[test['statuses']['overall']] += 1
            else:
                error += str(test)
            with log_path.join('no_status.log').open('a') as f:
                f.write(error)

        map(_inc_test_count, artifacts.values())
        report['test_counts'] = test_counts
        report['test_counts']['total'] = sum(test_counts.values())

        from fixtures.ui_coverage import ui_coverage_percent
        if ui_coverage_percent:
            report['ui_coverage_percent'] = ui_coverage_percent

        import json
        with test_report.open('w') as art_out:
            json.dump(report, art_out, indent=2)
