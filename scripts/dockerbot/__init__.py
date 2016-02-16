import re
import yaml


def parse_pr_metadata(pr_body):
    if not pr_body:
        return {}
    if not isinstance(pr_body, basestring):
        print "pr_body '%s' is not a string, %s" % (pr_body, type(pr_body))
        return {}
    metadata = re.findall("{{(.*?)}}", pr_body)
    if not metadata:
        return {}
    else:
        ydata = yaml.safe_load(metadata[0])
        return ydata
