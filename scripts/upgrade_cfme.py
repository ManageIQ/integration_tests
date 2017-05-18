#!/bin/python

import argparse
import yaml
import time
import threading
import requests
from datetime import datetime
from utils.appliance import IPAppliance
import logging

# setting script logging object
# logging all the event to script and progress messages to screen
formatter = "[%(asctime)s][%(levelname)s][%(funcName)s] - %(message)s"
log_name = "cfme-upgrade-{date}.log".format(date=datetime.now().strftime("%y:%m:%d::%H:%M:%y"))
logging.basicConfig(filename=log_name, filemode="w",
                    level=logging.DEBUG, format=formatter)
logger = logging.getLogger("cfme_logger")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(formatter))
logger.addHandler(console_handler)


class CfmeUpgradeManeger(IPAppliance):

    def __init__(self, appliance_ip, repo_list, dest_version):
        super(CfmeUpgradeManeger, self).__init__(address=appliance_ip)
        self.repo_list = repo_list
        self.dest_version = dest_version

    def exec_commaned(self, cmd, expect_failure=False, ignore_failure=False):
        '''
        execute command on the appliance and logging the command with it output to log file
        :param cmd: command
        :param expect_failure: is the command have to fail
        :param ignore_failure: not raise exception on command failure
        :return: command results
        '''

        logger.debug("exec_commaned: {cmd}".format(cmd=cmd))
        result = self.ssh_client.run_command(cmd)
        try:
            if bool(result.rc) != expect_failure and not ignore_failure:
                exception_msg = "command {cmd} failed!!\n\n\n" \
                                "{command_output}".format(cmd=cmd,
                                                          command_output=result.output)
                raise RuntimeError(exception_msg)
        except Exception as ex:
            logger.exception(ex.message)

        logger.debug(result.output)
        return result

    def add_yum_repo(self):
        '''
        setting all yumrepos before starting the ugrade
        :return: None
        '''

        logger.info("adding repositories to yum")
        for curr_repo_url in self.repo_list:
            # Add all the repos to yum repo
            self.exec_commaned("yum-config-manager "
                               "--add-repo {repo_url}".format(repo_url=curr_repo_url))

    def update_yum(self):
        '''
        initiate upgrading process
        :return: None
        '''
        def monitor_yum():
            '''
            give real time monitoring on yum update (give the user experience
            that the script is still running)
            :return: None
            '''

            time.sleep(5)
            # do as long yum is running on the appliance
            res = self.exec_commaned(""" ps -ef | grep "yum update" | grep -v grep """,
                                     ignore_failure=True)
            while not bool(res.rc):
                logger.info("yum still running")
                time.sleep(10)
                res = self.exec_commaned(""" ps -ef | grep "yum update" | grep -v grep """,
                                         ignore_failure=True)

        logger.info("importing all gpg keys for yum repositories")
        self.ssh_client.run_command("rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-*")

        # start thr monitoring thread
        monitor = threading.Thread(target=monitor_yum)
        monitor.start()

        logger.info("initiating yum update")
        self.ssh_client.run_command("yum update -y")

    def stop_cfme(self):
        '''
        stop CFME engine process
        :return:
        '''
        logger.info("stopping the cfme engine (evmserverd)")

        result = self.exec_commaned("systemctl status evmserverd | "
                                    "grep Active: | awk {'print $2'}", ignore_failure=True)

        if "active" in result.output:
            self.exec_commaned("systemctl stop evmserverd")

    def start_cfme(self):
        '''
        start CFME engine process
        :return: None
        '''
        logger.info("starting the cfme engine (evmserverd)")
        result = self.exec_commaned("systemctl status evmserverd | grep Active: | awk {'print $2'}",
                                    ignore_failure=True)

        if "inactive" in result.output:
            self.exec_commaned("systemctl start evmserverd")

    def yum_register(self, username, password):
        '''
        registaer to subscription manager
        :param username: username to sign with
        :param password: password to sign with
        :return: None
        '''
        self.exec_commaned("subscription-manager register --username={username} "
                           "--password={password} "
                           "--force".format(username=username, password=password))

    def validate_cfme_version(self):
        '''
        Validating if the cfme version  is fit
        :return:
        '''
        logger.info("waiting for 120 seconds for main process to load "
                    "before running version validation")
        time.sleep(120)
        logger.info("start CFME version validation")
        api_url = "https://{ip}/api/".format(ip=self.address)
        auth = ("admin", "smartvm")
        si = requests.get(api_url, verify=False, auth=auth).json()["server_info"]
        assert si['version'].split("-", 1)[0] == self.dest_version, "The upgrade filed!"
        logger.info("The upgrade finished successfully")

    def restart_components(self):
        logger.info("restarting componates after updating components")

        self.exec_commaned("systemctl restart $APPLIANCE_PG_SERVICE")

        self.ssh_client.run_rake_command("db:migrate")
        self.ssh_client.run_rake_command("evm:automate:reset")
        self.exec_commaned("systemctl restart rh-postgresql95-postgresql")


def main():
    parser = argparse.ArgumentParser(epilog=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-c", "--config", help="yaml file with configurations",
                        dest="config", action="store", default=False)
    args = parser.parse_args()

    params = {}
    try:
        logger.info("loading config file")
        with open(args.config, 'r') as stream:
            params = yaml.load(stream)
    except Exception as ex:
        logger.exception(ex.message)

    # filed name: (error msg, is mandatory, default value)
    requierd_fildes = {"address": {"msg": "Appliance address is missing",
                                   "is_mandatory": True, "default": None},
                       "username": {"msg": "subscription manager user name is missing",
                                    "is_mandatory": True, "default": None},
                       "password": {"msg": "subscription manager password is missing",
                                    "is_mandatory": True, "default": None},
                       "skip_validation": {"msg": "skip validation key not found on config file, "
                                           "assuming version validation is required",
                                           "is_mandatory": False, "default": True},
                       "dest_version": {"msg": "destination version is missing"
                       if not params.get("skip_validation", False) else "",
                                        "is_mandatory": not params.get("skip_validation", False),
                                        "default": None},
                       "repo": {"msg": "repolist is missing",
                                "is_mandatory": True, "default": None}}
    for key in requierd_fildes:
        if key not in params:
            try:
                if requierd_fildes[key]["is_mandatory"]:
                    raise RuntimeError(requierd_fildes.get(key).get("msg"))
            except Exception as ex:
                logger.exception(ex.message)
            else:
                params.update({key: requierd_fildes.get(key).get("default")})

    logger.info("Starting system upgrade")
    cfme_upgrader = CfmeUpgradeManeger(params["address"],
                                       repo_list=params["repo"],
                                       dest_version=params["dest_version"])

    cfme_upgrader.add_yum_repo()
    cfme_upgrader.stop_cfme()
    cfme_upgrader.yum_register(params["username"], params["password"])
    cfme_upgrader.update_yum()
    cfme_upgrader.restart_components()
    cfme_upgrader.start_cfme()

    if params["skip_validation"]:
        cfme_upgrader.validate_cfme_version()


if __name__ == '__main__':
    main()
