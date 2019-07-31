import inspect
import operator
import re
import subprocess
from collections import defaultdict

from cfme.fixtures.artifactor_plugin import fire_art_test_hook
from cfme.fixtures.pytest_store import store


def dig_code(node):
    code_data = inspect.getsourcelines(node.function)
    lineno = code_data[1]
    offset = len(code_data[0])
    filename = inspect.getfile(node.function)
    line_param = '-L {},+{}'.format(lineno, offset)
    cmd_params = ['git', 'blame', line_param, filename, '--show-email']

    proc = subprocess.Popen(cmd_params, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()
    lc_info = proc.stdout.readlines()
    contact_stats = defaultdict(int)
    for line in lc_info:
        contact = re.findall(r'.{8} \(\<(.*?)\> ', line)
        contact_stats[contact[0]] += 1
    sorted_x = sorted(list(contact_stats.items()), key=operator.itemgetter(1), reverse=True)
    results = []
    for item in sorted_x:
        percen = float(item[1]) / float(offset) * 100
        record = (item[0], percen)
        results.append(record)
    return results


def pytest_runtest_teardown(item, nextitem):
    qa_string = "Unknown,None"
    if hasattr(item, "_metadata") and item._metadata.get('owner') is not None:
        # The owner is specified in metadata
        qa_string = "{},from metadata"
    else:
        try:
            qa_arr = []
            results = dig_code(item)
            for idx in range(min(2, len(results))):
                qa_arr.append("{},{:.2f}%\n".format(results[idx][0], results[idx][1]))
            if qa_arr:
                qa_string = "".join(qa_arr)
        except Exception:
            pass
    fire_art_test_hook(
        item,
        'filedump', description="QA Contact",
        contents=str(qa_string), file_type="qa_contact", group_id="qa-contact",
        slaveid=store.slaveid)
    # group_id is not used for qa contact now, but thinking into the future
