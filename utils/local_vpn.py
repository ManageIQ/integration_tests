# -*- coding: utf-8 -*-
import time
from contextlib import contextmanager
from subprocess import Popen
from Runner import Run

from utils import conf, path
from utils.log import logger
from utils.randomness import generate_random_string


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
        assert Run.command("cd {}; tar xfv tmp.tar.gz".format(tmpdir))
        log_filename = "openvpn-{}.log".format(generate_random_string())
        logger.info("OpenVPN log: {}".format(log_filename))
        with path.log_path.join(log_filename).open("w") as log:
            openvpn = Popen(
                "cd {}; sudo -n openvpn --config user.conf".format(tmpdir),
                shell=True, stdout=log)
            time.sleep(5)
            assert openvpn.poll() is None, "OpenVPN died! (maybe needs no-password sudo?)"
            yield
            openvpn.terminate()
            openvpn.wait()
        Run.command("rm -rf {}".format(tmpdir))
