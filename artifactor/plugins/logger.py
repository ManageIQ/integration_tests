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

    class Test(object):
        def __init__(self, ident):
            self.ident = ident
            self.in_progress = False
            self.logger = None

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('log_message', self.log_message)

    def configure(self):
        self.configured = True
        self.tests = {}
        self.level = self.data.get('level', 'DEBUG')

    @ArtifactorBasePlugin.check_configured
    def start_test(self, artifact_path, test_name, test_location, slaveid):
        if not slaveid:
            slaveid = "Master"
        test_ident = "{}/{}".format(test_location, test_name)
        if slaveid in self.tests:
            if self.tests[slaveid].in_progress:
                print "Test already running, can't start another"
                return None
        self.tests[slaveid] = self.Test(slaveid)
        self.tests[slaveid].in_progress = True
        artifacts = []
        os_filename = self.ident + "-" + "cfme.log"
        os_filename = os.path.join(artifact_path, os_filename)
        if os.path.isfile(os_filename):
            os.remove(os_filename)
        artifacts.append(os_filename)
        self.tests[slaveid].logger = create_logger(self.ident + test_name, os_filename)
        self.tests[slaveid].logger.setLevel(self.level)

        return None, {'artifacts': {test_ident: {'files': {self.ident: artifacts}}}}

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name, test_location, slaveid):
        if not slaveid:
            slaveid = "Master"
        self.tests[slaveid].in_progress = False
        pass

    @ArtifactorBasePlugin.check_configured
    def log_message(self, log_record, slaveid):
        if not slaveid:
            slaveid = "Master"
        if self.tests[slaveid]:
            if self.tests[slaveid].logger:
                fn = getattr(self.tests[slaveid].logger, log_record['level'])
                fn(log_record['message'], extra=log_record['extra'])
