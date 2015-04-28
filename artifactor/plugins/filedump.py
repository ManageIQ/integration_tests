""" FileDump plugin for Artifactor

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    overwrite: True
    plugins:
        filedump:
            enabled: True
            plugin: filedump
"""

from artifactor import ArtifactorBasePlugin
import base64
import os


class Filedump(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('filedump', self.filedump)
        self.register_plugin_hook('sanitize', self.sanitize)

    def configure(self):
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def filedump(self, artifact_path, filename, contents, test_name, test_location, fd_ident,
                 mode="w", contents_base64=False):
        artifacts = []
        os_filename = self.ident + "-" + filename
        os_filename = os.path.join(artifact_path, os_filename)
        if os.path.isfile(os_filename):
            os.remove(os_filename)
        artifacts.append(os_filename)
        with open(os_filename, mode) as f:
            if contents_base64:
                contents = base64.b64decode(contents)
            f.write(contents)
        test_ident = "{}/{}".format(test_location, test_name)
        return None, {'artifacts': {test_ident: {'files': {fd_ident: artifacts}}}}

    @ArtifactorBasePlugin.check_configured
    def sanitize(self, test_location, test_name, artifacts, fd_idents, words):
        test_ident = "{}/{}".format(test_location, test_name)
        filename = None
        try:
            for fd_ident in fd_idents:
                filenames = artifacts[test_ident]['files'][fd_ident]
                for filename in filenames:
                    with open(filename) as f:
                        data = f.read()
                    for word in words:
                        data = data.replace(word, "*" * len(word))
                    with open(filename, "w") as f:
                        f.write(data)
        except KeyError:
            pass
