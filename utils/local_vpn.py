# -*- coding: utf-8 -*-
import time
from contextlib import contextmanager
from subprocess import Popen
from Runner import Run

from utils import conf, path
from utils.log import logger
from utils.randomness import generate_random_string
from utils.wait import wait_for


@contextmanager
def vpn_for(provider_key):
    provider_data = conf.cfme_data.management_systems[provider_key]
    if "vpn" not in provider_data:
        yield
    else:
        assert Run.command("rpm -qa | grep ^openvpn", shell=True), "OpenVPN not installed locally!"
        tmpdir = "/tmp/{}".format(generate_random_string())
        logger.info("OpenVPN temporary directory: {}".format(tmpdir))
        assert Run.command("mkdir -p {}".format(tmpdir))
        assert Run.command(
            "wget -O {}/tmp.tar.gz {}".format(tmpdir, provider_data["vpn"]["test_machine"]))
        assert Run.command("cd {}; tar xfv tmp.tar.gz".format(tmpdir), shell=True)
        log_filename = "openvpn-{}.log".format(generate_random_string())
        logger.info("OpenVPN log: {}".format(log_filename))
        with path.log_path.join(log_filename).open("w") as log:
            logger.info("OpenVPN starting!")
            openvpn = Popen(
                "cd {} && exec sudo -n openvpn --config user.conf".format(tmpdir),
                shell=True, stdout=log)
            time.sleep(5)
            assert openvpn.poll() is None, "OpenVPN died! (maybe needs no-password sudo?)"
            logger.info("OpenVPN ready! (PID: {})".format(openvpn.pid))
            yield
            logger.info("OpenVPN shutting down")
            Run.command("sudo -n kill -2 {}".format(openvpn.pid))
            wait_for(
                lambda: Run.command("sudo kill -0 {}".format(openvpn.pid)),
                fail_condition=lambda x: not x, num_sec=10, delay=0.5)
            rc = openvpn.poll()
            logger.info("OpenVPN ended with code {}".format(rc))
        Run.command("rm -rf {}".format(tmpdir))
