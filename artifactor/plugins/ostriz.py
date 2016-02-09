from artifactor import ArtifactorBasePlugin
import requests
import json


def overall_test_status(statuses):
    # Handle some logic for when to count certain tests as which state
    for when, status in statuses.iteritems():
        if when == "call" and status[1] and status[0] == "skipped":
            return "xfailed"
        elif when == "call" and status[1] and status[0] == "failed":
            return "xpassed"
        elif (when == "setup" or when == "teardown") and status[0] == "failed":
            return "error"
        elif status[0] == "skipped":
            return "skipped"
        elif when == "call" and status[0] == 'failed':
            return "failed"
    return "passed"


class Ostriz(ArtifactorBasePlugin):

    def plugin_initialize(self):
        self.register_plugin_hook('ostriz_send', self.ostriz_send)

    def configure(self):
        self.url = self.data.get('url', None)
        self.configured = True

    @ArtifactorBasePlugin.check_configured
    def ostriz_send(self, artifacts, test_location, test_name, slaveid, run_id, version, build,
            stream):
        test_ident = "{}/{}".format(test_location, test_name)
        json_data = artifacts[test_ident]
        json_data['name'] = test_ident
        json_data['run'] = run_id
        json_data['slaveid'] = slaveid
        json_data['source'] = self.data['source']
        json_data['version'] = version
        json_data['build'] = build
        json_data['stream'] = stream
        json_data['method'] = "automated"
        requests.post(self.url, data=json.dumps(json_data))
        return None, None
