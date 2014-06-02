""" Logger plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    overwrite: True
    plugins:
        logger:
            enabled: True
            plugin: logger
            level: DEBUG
"""

from artifactor.utils import ArtifactorBasePlugin
import os
from utils.log import create_logger


class Logger(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('log_message', self.log_message)

    def configure(self):
        self.configured = True
        self.test_in_progress = False
        self.current_logger = None
        self.level = self.data.get('level', 'DEBUG')

    @ArtifactorBasePlugin.check_configured
    def start_test(self, artifact_path, test_name, test_location):
        if self.test_in_progress:
            print "Test already running, can't start another"
            return None
        artifacts = []
        os_filename = self.ident + "-" + "cfme.log"
        os_filename = os.path.join(artifact_path, os_filename)
        if os.path.isfile(os_filename):
            os.remove(os_filename)
        artifacts.append(os_filename)
        self.current_logger = create_logger(self.ident + test_name, os_filename)
        self.current_logger.setLevel(self.level)

        self.test_in_progress = True
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'files': {self.ident: artifacts}}}}

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name):
        """Finish test"""
        self.test_in_progress = False

    @ArtifactorBasePlugin.check_configured
    def log_message(self, log_record):
        if self.current_logger:
            fn = getattr(self.current_logger, log_record['level'])
            fn(log_record['message'], extra=log_record['extra'])
