import re
import yaml


def parse_pr_metadata(pr_body):
    metadata = re.findall("{{(.*?)}}", pr_body)
    if not metadata:
        return {}
    else:
        ydata = yaml.safe_load(metadata[0])
        return ydata
