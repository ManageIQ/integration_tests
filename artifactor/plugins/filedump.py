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

from artifactor.utils import ArtifactorBasePlugin
import base64
import os


class Filedump(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('filedump', self.filedump)

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
