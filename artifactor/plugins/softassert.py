""" SoftAssert plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    overwrite: True
    plugins:
        softassert:
            enabled: True
            plugin: softassert

Requires the filedump plugin
"""

from artifactor.utils import ArtifactorBasePlugin
import os.path
import os


class SoftAssert(ArtifactorBasePlugin):

    class Test(object):
        def __init__(self, ident):
            self.ident = ident
            self.in_progress = False
            self.assert_artifacts = []

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('add_assertion', self.add_assertion)

    def configure(self):
        self.tests = {}
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def start_test(self, test_name, test_location):
        """Start a test"""
        test_ident = "{}/{}".format(test_location, test_name)
        if test_ident in self.tests:
            if self.tests[test_ident].in_progress:
                print "Test already running, can't start another"
                return None
        else:
            self.tests[test_ident] = self.Test(test_ident)
        self.tests[test_ident].in_progress = True

    @ArtifactorBasePlugin.check_configured
    def add_assertion(self, test_name, test_location, artifacts):
        test_ident = "{}/{}".format(test_location, test_name)
        self.tests[test_ident].assert_artifacts.append(artifacts)
        return None, None

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name, test_location):
        """Finish test"""
        test_ident = "{}/{}".format(test_location, test_name)

        artifacts = []
        for idx, assertion in enumerate(self.tests[test_ident].assert_artifacts):
            filename_mapping = {'full_tb': '{}-assert_traceback.log'.format(idx),
                                'screenshot': '{}-assert_screenshot.png'.format(idx),
                                'screenshot_error': '{}-assert_screenshot.txt'.format(idx)}
            assert_files = {}
            for item in filename_mapping:
                data = assertion.get(item, None)
                if data:
                    os_filename = filename_mapping[item]
                    os_filename = os.path.join(artifact_path, os_filename)
                    with open(os_filename, "wb") as f:
                        f.write(data.decode('base64'))
                    assert_files[item] = os_filename
            artifacts.append(assert_files)
        del self.tests[test_ident]
        return None, {'artifacts': {
            test_ident: {'files': {
                self.ident: artifacts}}}}
