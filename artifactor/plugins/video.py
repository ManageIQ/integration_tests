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

from artifactor.utils import ArtifactorBasePlugin
import os
from utils.video import Recorder


class Video(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('finish_session', self.finish_session)

    def configure(self):
        self.configured = True
        self.test_in_progress = False
        self.current_recorder = None
        self.quality = self.data.get('quality', '10')
        self.display = self.data.get('display', ':0')

    @ArtifactorBasePlugin.check_configured
    def start_test(self, artifact_path, test_name, test_location):
        if self.test_in_progress:
            print "Test already running, can't start another"
            return None
        artifacts = []
        os_filename = self.ident + "-" + self.ident + ".ogv"
        os_filename = os.path.join(artifact_path, os_filename)
        if os.path.isfile(os_filename):
            os.remove(os_filename)
        artifacts.append(os_filename)
        try:
            self.current_recorder = Recorder(os_filename, display=self.display,
                                             quality=self.quality)
            self.current_recorder.start()
        except:
            pass
        self.test_in_progress = True
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'files': {self.ident: artifacts}}}}

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name):
        """Finish test"""
        try:
            self.current_recorder.stop()
        except:
            pass
        self.test_in_progress = False

    def finish_session(self):
        try:
            self.current_recorder.stop()
        except:
            pass
