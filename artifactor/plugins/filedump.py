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
import re

from utils import normalize_text, safe_string


class Filedump(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('filedump', self.filedump)
        self.register_plugin_hook('sanitize', self.sanitize)
        self.register_plugin_hook('pre_start_test', self.start_test)
        self.register_plugin_hook('finish_test', self.finish_test)

    def configure(self):
        self.configured = True

    def start_test(self, artifact_path, test_name, test_location, slaveid):
        if not slaveid:
            slaveid = "Master"
        self.store[slaveid] = {
            "artifact_path": artifact_path,
            "test_name": test_name,
            "test_location": test_location
        }

    def finish_test(self, artifact_path, test_name, test_location, slaveid):
        if not slaveid:
            slaveid = "Master"

    @ArtifactorBasePlugin.check_configured
    def filedump(self, description, contents, slaveid=None, mode="w", contents_base64=False,
                 display_type="primary", display_glyph=None, file_type=None,
                 dont_write=False, os_filename=None, group_id=None, test_name=None,
                 test_location=None):
        if slaveid is not None:
            if not slaveid:
                slaveid = "Master"
            test_ident = "{}/{}".format(self.store[slaveid]['test_location'],
                self.store[slaveid]['test_name'])
        else:
            test_ident = "{}/{}".format(test_location, test_name)
        artifacts = []
        if os_filename is None:
            safe_name = re.sub(r"\s+", "_", normalize_text(safe_string(description)))
            os_filename = self.ident + "-" + safe_name
            os_filename = os.path.join(self.store[slaveid]['artifact_path'], os_filename)
            if file_type is not None and "screenshot" in file_type:
                os_filename = os_filename + ".png"
            elif file_type is not None and (
                    "_tb" in file_type or "traceback" in file_type or file_type == "log"):
                os_filename = os_filename + ".log"
            elif file_type is not None and file_type == "html":
                os_filename = os_filename + ".html"
            elif file_type is not None and file_type == "video":
                os_filename = os_filename + ".ogv"
            else:
                os_filename = os_filename + ".txt"
        artifacts.append({
            "file_type": file_type,
            "display_type": display_type,
            "display_glyph": display_glyph,
            "description": description,
            "os_filename": os_filename,
            "group_id": group_id,
        })
        if not dont_write:
            if os.path.isfile(os_filename):
                os.remove(os_filename)
            with open(os_filename, mode) as f:
                if contents_base64:
                    contents = base64.b64decode(contents)
                f.write(contents)

        return None, {'artifacts': {test_ident: {'files': artifacts}}}

    @ArtifactorBasePlugin.check_configured
    def sanitize(self, test_location, test_name, artifacts, words):
        test_ident = "{}/{}".format(test_location, test_name)
        filename = None
        try:
            for f in artifacts[test_ident]['files']:
                if f["file_type"] not in {
                        "traceback", "short_tb", "func_trace", "rbac", "soft_traceback",
                        "soft_short_tb"}:
                    continue
                filename = f["os_filename"]
                with open(filename) as f:
                    data = f.read()
                for word in words:
                    if not isinstance(word, basestring):
                        word = str(word)
                    data = data.replace(word, "*" * len(word))
                with open(filename, "w") as f:
                    f.write(data)
        except KeyError:
            pass
