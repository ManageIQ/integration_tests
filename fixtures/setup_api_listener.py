# -*- coding: utf8 -*-
# pylint: disable=E1101
import pytest
import subprocess
import logging
import time

logging.basicConfig(filename='test_events.log', level=logging.INFO)


@pytest.fixture(scope="module", autouse=True)
def setup_api_listener(request):
    '''start a python bottle api server (the listener) to cache cfme events
    '''
    listener_script = "/usr/bin/env python %s/tests/common/listener.py" % \
                        request.session.fspath
    logging.info("Starting listener...\n%s" % listener_script)
    listener = subprocess.Popen(listener_script,
                                stderr=subprocess.PIPE,
                                shell=True)
    logging.info("(%s)\n" % listener.pid)

    def teardown():
        logging.info("\nKilling listener (%s)..." % (listener.pid))
        listener.kill()
        (stdout, stderr) = listener.communicate()
        logging.info("%s\n%s" % (stdout, stderr))
    request.addfinalizer(teardown)
    time.sleep(1)
