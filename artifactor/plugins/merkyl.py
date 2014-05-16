""" Merkyl plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    overwrite: True
    plugins:
        merkyl:
            enabled: False
            plugin: merkyl
            port: 8192
            log_files:
                - /var/www/miq/vmdb/log/evm.log
                - /var/www/miq/vmdb/log/production.log
                - /var/www/miq/vmdb/log/automation.log
"""

from artifactor.utils import ArtifactorBasePlugin
import os.path
import requests
from requests.exceptions import ConnectionError


class Merkyl(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('start_session', self.start_session)
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('finish_session', self.finish_session)

    def configure(self, ip=None, files=None, port=None):
        self.ip = ip
        self.files = files
        self.port = port
        self.configured = True
        self.test_in_progress = False

    @ArtifactorBasePlugin.check_configured
    def start_test(self):
        """Start a test"""
        if self.test_in_progress:
            print "Test already running, can't start another"
            return None
        try:
            url = "http://{}:{}/resetall".format(self.ip, self.port)
            requests.get(url, timeout=15)
        except ConnectionError:
            print "Unable to connect"
        self.test_in_progress = True

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name):
        """Finish test"""
        artifacts = []
        for filename in self.files:
            base, tail = os.path.split(filename)
            os_filename = tail + "-" + self.ident + ".log"
            os_filename = os.path.join(artifact_path, os_filename)
            with open(os_filename, "w") as f:
                url = "http://{}:{}/get/{}".format(self.ip, self.port, tail)
                try:
                    doc = requests.get(url, timeout=15)
                    content = doc.content
                except:
                    content = ""
                f.write(content)
            artifacts.append(os_filename)
        self.test_in_progress = False
        return None, {'artifacts': {test_name: {self.ident: artifacts}}}

    @ArtifactorBasePlugin.check_configured
    def start_session(self, run_id):
        """Session started"""
        for file_name in self.files:
            try:
                url = "http://{}:{}/setup{}".format(self.ip, self.port, file_name)
                requests.get(url, timeout=15)
            except ConnectionError:
                print "Unable to connect"

    @ArtifactorBasePlugin.check_configured
    def finish_session(self, artifacts):
        """Session finished"""
        for filename in self.files:
            base, tail = os.path.split(filename)
            try:
                url = "http://{}:{}/delete/{}".format(self.ip, self.port, tail)
                requests.get(url, timeout=15)
            except ConnectionError:
                print "Unable to connect"
