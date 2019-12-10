import json

import requests

from artifactor import ArtifactorBasePlugin


def overall_test_status(statuses):
    # Handle some logic for when to count certain tests as which state
    for when, status in statuses.items():
        if when == "call" and status[1] and status[0] == "skipped":
            return "xfailed"
        elif when == "call" and status[1] and status[0] == "failed":
            return "xpassed"
        elif (when == "setup" or when == "teardown") and status[0] == "failed":
            return "error"
        elif status[0] == "skipped":
            return "skipped"
        elif when == "call" and status[0] == "failed":
            return "failed"
    return "passed"


class Ostriz(ArtifactorBasePlugin):
    def plugin_initialize(self):
        self.register_plugin_hook("ostriz_send", self.ostriz_send)

    def configure(self):
        self.url = self.data.get("url")
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def ostriz_send(
        self,
        artifacts,
        test_location,
        test_name,
        slaveid,
        polarion_ids,
        run_id,
        version,
        build,
        stream,
        jenkins=None,
        env_params=None,
    ):
        env_params = env_params or {}
        test_ident = "{}/{}".format(test_location, test_name)
        json_data = artifacts[test_ident]
        json_data["name"] = test_ident
        json_data["run"] = run_id
        json_data["slaveid"] = slaveid
        json_data["source"] = self.data["source"]
        json_data["version"] = version
        json_data["build"] = build.strip()
        json_data["stream"] = stream
        json_data["method"] = "automated"
        json_data["jenkins"] = jenkins or None
        # Either None or a list of Polarion Test Case IDs
        json_data["polarion"] = polarion_ids
        if not json_data.get("params"):
            json_data["params"] = {}
        json_data["params"].update(env_params)
        requests.post(self.url, data=json.dumps(json_data))
        return None, None
