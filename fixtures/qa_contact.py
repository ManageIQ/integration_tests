from collections import defaultdict
import inspect
import subprocess
import re
import operator
from fixtures.artifactor_plugin import art_client, get_test_idents


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
        contact = re.findall('.{8} \(\<(.*?)\> ', line)
        contact_stats[contact[0]] += 1
    sorted_x = sorted(contact_stats.items(), key=operator.itemgetter(1), reverse=True)
    results = []
    for item in sorted_x:
        percen = float(item[1]) / float(offset) * 100
        record = (item[0], percen)
        results.append(record)
    return results


def pytest_exception_interact(node, call, report):
    name, location = get_test_idents(node)
    if hasattr(node, "_metadata") and node._metadata.get('owner') is not None:
        # The owner is specified in metadata
        art_client.fire_hook(
            'filedump', test_location=location, test_name=name, filename="qa_contact.txt",
            contents="{},from metadata".format(node._metadata.owner), fd_ident="qa")
        return
    try:
        qa_arr = []
        results = dig_code(node)
        for idx in range(min(2, len(results))):
            qa_arr.append("{},{:.2f}%\n".format(results[idx][0], results[idx][1]))
        qa_string = "".join(qa_arr)

    except:
        qa_string = "Unknown"
    art_client.fire_hook('filedump', test_location=location, test_name=name,
                         filename="qa_contact.txt", contents=str(qa_string), fd_ident="qa")
