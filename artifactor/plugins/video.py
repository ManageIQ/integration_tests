""" Video plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    overwrite: True
    plugins:
        video:
            enabled: True
            plugin: video
            quality: 10
            display: ":99"
"""

from artifactor import ArtifactorBasePlugin
import os
from utils.video import Recorder


class Video(ArtifactorBasePlugin):

    class Test(object):
        def __init__(self, ident):
            self.ident = ident
            self.in_progress = False
            self.recorder = None

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('encode', self.encode, bg=True)
        self.register_plugin_hook('finish_session', self.finish_session)

    def configure(self):
        self.configured = True
        self.tests = {}
        self.quality = self.data.get('quality', '10')
        self.display = self.data.get('display', ':0')
        self.encoder = self.data.get('encoder')
        self.rtype = self.data.get('type', 'xfb')

    @ArtifactorBasePlugin.check_configured
    def start_test(self, artifact_path, test_name, test_location):
        test_ident = "{}/{}".format(test_location, test_name)
        if test_ident in self.tests:
            if self.tests[test_ident].in_progress:
                print "Test already running, can't start another"
                return None
        else:
            self.tests[test_ident] = self.Test(test_ident)
            self.tests[test_ident].in_progress = True
        artifacts = []
        os_filename = self.ident + ".ogv"
        os_filename = os.path.join(artifact_path, os_filename)
        if os.path.isfile(os_filename):
            os.remove(os_filename)
        artifacts.append(os_filename)
        try:
            self.tests[test_ident].recorder = Recorder(os_filename, display=self.display,
                                                       quality=self.quality, rtype=self.rtype,
                                                       encoder=self.encoder)
            self.tests[test_ident].recorder.start()
        except:
            pass
        self.tests[test_ident].in_progress = True
        return None, {'artifacts': {test_ident: {'files': {self.ident: artifacts}}}}

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name, test_location):
        """Finish test"""
        test_ident = "{}/{}".format(test_location, test_name)
        try:
            self.tests[test_ident].recorder.stop()
        except:
            pass
        if self.rtype == 'xfb':
            del self.tests[test_ident]

    @ArtifactorBasePlugin.check_configured
    def encode(self, test_name, test_location):
        test_ident = "{}/{}".format(test_location, test_name)
        if self.rtype == 'vnc':
            try:
                self.tests[test_ident].recorder.encode()
            except:
                raise
            del self.tests[test_ident]

    def finish_session(self):
        try:
            for test in self.tests:
                test.recorder.stop()
        except:
            pass
