""" Multi screenshot plugin for Artifactor

This plugin enables you to store multiple screenshots inside your test run. Comes with a
:py:func:`fixtures.screenshots.take_screenshot` fixture to take screenshots.

Developed mainly for the :py:class:`utils.appliance.IPAppliance` which will destroy the browser
once you exit the context manager, therefore obscuring the original error.

Add a stanza to the artifactor config like this,
artifactor:
    log_dir: /home/username/outdir
    per_run: test #test, run, None
    overwrite: True
    plugins:
        screenshots:
            enabled: True
            plugin: screenshots

Requires the filedump plugin
"""

from artifactor import ArtifactorBasePlugin

from collections import namedtuple
from utils import safe_string, normalize_text
import os.path
import os
import re


class MultiScreenshots(ArtifactorBasePlugin):
    Screenshot = namedtuple("Screenshot", ["name", "screenshot", "screenshot_error", "traceback"])

    class Result(object):
        def __init__(self, name):
            self.name = name
            self.screenshot = None
            self.traceback = None

    def plugin_initialize(self):
        self.register_plugin_hook('finish_test', self.finish_test)
        self.register_plugin_hook('add_screenshot', self.add_screenshot)

    def configure(self):
        self.screenshots = {}
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def add_screenshot(self, test_name, test_location, artifacts):
        test_ident = "{}/{}".format(test_location, test_name)
        if test_ident not in self.screenshots:
            self.screenshots[test_ident] = []
        self.screenshots[test_ident].append(
            self.Screenshot(
                artifacts["name"], artifacts.get("screenshot", None),
                artifacts.get("screenshot_error", None), artifacts.get("traceback", None)))
        return None, None

    @ArtifactorBasePlugin.check_configured
    def finish_test(self, artifact_path, test_name, test_location):
        test_ident = "{}/{}".format(test_location, test_name)

        artifacts = []
        try:
            screenshots = self.screenshots[test_ident]
        except KeyError:
            screenshots = []
        for screenshot in screenshots:
            name = screenshot.name
            safe_name = re.sub(r"\s+", "_", normalize_text(safe_string(name)))
            filename_mapping = {
                "traceback": "multiss-{}.log".format(safe_name),
                "screenshot": "multiss-{}.png".format(safe_name),
                "screenshot_error": "multiss-{}.txt".format(safe_name),
            }
            result = {
                "name": name,
                "screenshot": None,
                "traceback": None,
            }
            include_result = False
            for attr_name, filename in filename_mapping.iteritems():
                data = getattr(screenshot, attr_name, None)
                if data:
                    os_filename = os.path.join(artifact_path, filename)
                    with open(os_filename, "wb") as f:
                        f.write(data.decode("base64"))
                    if attr_name == "traceback":
                        result["traceback"] = os_filename
                        include_result = True
                    elif attr_name in {"screenshot", "screenshot_error"}:
                        result["screenshot"] = os_filename
                        include_result = True
            if include_result:
                artifacts.append(result)
        try:
            del self.screenshots[test_ident]
        except KeyError:
            pass

        return None, {"artifacts": {test_ident: {"screenshots": artifacts}}}
