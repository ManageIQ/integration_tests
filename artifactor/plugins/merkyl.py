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

from artifactor import ArtifactorBasePlugin
import os.path
import requests


class Merkyl(ArtifactorBasePlugin):

    class Test(object):
        def __init__(self, ident, ip, port):
            self.ident = ident
            self.ip = ip
            self.port = port
            self.in_progress = False
            self.extra_files = set()

    def plugin_initialize(self):
        self.register_plugin_hook('setup_merkyl', self.start_session)
        self.register_plugin_hook('start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('teardown_merkyl', self.finish_session)
        self.register_plugin_hook('get_log_merkyl', self.get_log)
        self.register_plugin_hook('add_log_merkyl', self.add_log)

    def configure(self):
        self.files = self.data.get('log_files', [])
        self.port = self.data.get('port', '8192')
        self.tests = {}
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def start_test(self, test_name, test_location, ip):
        test_ident = "{}/{}".format(test_location, test_name)
        if test_ident in self.tests:
            if self.tests[test_ident].in_progress:
                print "Test already running, can't start another"
                return None
        else:
            self.tests[test_ident] = self.Test(test_ident, ip, self.port)
        url = "http://{}:{}/resetall".format(ip, self.port)
        requests.get(url, timeout=15)

        self.tests[test_ident].in_progress = True

    @ArtifactorBasePlugin.check_configured
    def get_log(self, test_name, test_location, filename):
        test_ident = "{}/{}".format(test_location, test_name)
        ip = self.tests[test_ident].ip

        base, tail = os.path.split(filename)
        url = "http://{}:{}/get/{}".format(ip, self.port, tail)
        doc = requests.get(url, timeout=15)
        content = doc.content
        return {'merkyl_content': content}, None

    @ArtifactorBasePlugin.check_configured
    def add_log(self, test_name, test_location, filename):
        test_ident = "{}/{}".format(test_location, test_name)
        ip = self.tests[test_ident].ip

        if filename not in self.files:
            self.tests[test_ident].extra_files.update([filename])
            url = "http://{}:{}/setup{}".format(ip, self.port, filename)
            requests.get(url, timeout=15)

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name, test_location, ip):
        test_ident = "{}/{}".format(test_location, test_name)
        artifacts = []
        for filename in self.files:
            _, tail = os.path.split(filename)
            os_filename = self.ident + "-" + tail + ".log"
            os_filename = os.path.join(artifact_path, os_filename)
            with open(os_filename, "w") as f:
                url = "http://{}:{}/get/{}".format(ip, self.port, tail)
                doc = requests.get(url, timeout=15)
                content = doc.content
                f.write(content)
                artifacts.append(os_filename)

        for filename in self.tests[test_ident].extra_files:
            _, tail = os.path.split(filename)
            os_filename = self.ident + "-" + tail + ".log"
            os_filename = os.path.join(artifact_path, os_filename)
            with open(os_filename, "w") as f:
                url = "http://{}:{}/get/{}".format(ip, self.port, tail)
                doc = requests.get(url, timeout=15)
                content = doc.content
                f.write(content)
                artifacts.append(os_filename)

            url = "http://{}:{}/delete/{}".format(ip, self.port, tail)
            requests.get(url, timeout=15)

        del self.tests[test_ident]
        return None, {'artifacts': {test_ident: {'files': {self.ident: artifacts}}}}

    @ArtifactorBasePlugin.check_configured
    def start_session(self, ip):
        """Session started"""
        for file_name in self.files:
            url = "http://{}:{}/setup{}".format(ip, self.port, file_name)
            requests.get(url, timeout=15)

    @ArtifactorBasePlugin.check_configured
    def finish_session(self, ip):
        """Session finished"""
        for filename in self.files:
            base, tail = os.path.split(filename)
            url = "http://{}:{}/delete/{}".format(ip, self.port, tail)
            requests.get(url, timeout=15)
