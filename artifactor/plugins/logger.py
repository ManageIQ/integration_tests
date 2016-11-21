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
import os
from logging import makeLogRecord
from artifactor import ArtifactorBasePlugin
from utils.log import make_file_handler


class Logger(ArtifactorBasePlugin):

    class Test(object):
        def __init__(self, ident):
            self.ident = ident
            self.in_progress = False
            self.handler = None

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('log_message', self.log_message)

    def configure(self):
        self.configured = True
        self.level = self.data.get('level', 'DEBUG')

    @ArtifactorBasePlugin.check_configured
    def start_test(self, artifact_path, test_name, test_location, slaveid):
        if not slaveid:
            slaveid = "Master"
        test_ident = "{}/{}".format(test_location, test_name)
        if slaveid in self.store:
            if self.store[slaveid].in_progress:
                print("Test already running, can't start another, logger")
                return None
        self.store[slaveid] = self.Test(test_ident)
        self.store[slaveid].in_progress = True
        filename = "{ident}-cfme.log".format(ident=self.ident)
        self.store[slaveid].handler = make_file_handler(
            filename,
            root=artifact_path,
            # we overwrite
            mode='w',
            level=self.level)

        self.fire_hook('filedump', test_location=test_location, test_name=test_name,
            description="cfme.log", slaveid=slaveid, contents="", file_type="log",
            display_glyph="align-justify", dont_write=True,
            os_filename=os.path.join(artifact_path, filename),
            group_id="pytest-logfile")

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name, test_location, slaveid):
        if not slaveid:
            slaveid = "Master"
        self.store[slaveid].in_progress = False

    @ArtifactorBasePlugin.check_configured
    def log_message(self, log_record, slaveid):
        record = makeLogRecord(log_record)  # hack
        if not slaveid:
            slaveid = "Master"
        if slaveid in self.store:
            handler = self.store[slaveid].handler
            if handler and record.levelno >= handler.level:
                handler.handle(record)
