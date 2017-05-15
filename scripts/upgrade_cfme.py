import argparse
import yaml
import time
import threading
import requests
from utils.appliance import IPAppliance


class cfme_upgrade_maneger(IPAppliance):

    def __init__(self, appliance_ip, repo_list, dest_version):
        super(cfme_upgrade_maneger, self).__init__(address=appliance_ip)
        self.repo_list = repo_list
        self.dest_version = dest_version

    def exec_commaned(self, cmd, expect_failure=False, ignore_failure=False):
        result = self.ssh_client.run_command(cmd)
        if bool(result.rc) != expect_failure and not ignore_failure:
            raise RuntimeError(
                "command {cmd} failed!!\n\n\n{command_output}".format(cmd=cmd,
                                                                      command_output=result.output))
        return result

    def add_yum_repo(self):
        print "adding repositories to yum"
        for curr_repo_url in self.repo_list:
            # Add all the repos to yum repo
            self.exec_commaned("yum-config-manager "
                               "--add-repo {repo_url}".format(repo_url=curr_repo_url))

    def update_yum(self):

        def monitor_yum():
            time.sleep(5)
            # do as long yum is running on the appliance
            res = self.exec_commaned(""" ps -ef | grep "yum update" | grep -v grep """,
                                     ignore_failure=True)
            while not bool(res.rc):
                print "yum still running"
                time.sleep(10)
                res = self.exec_commaned(""" ps -ef | grep "yum update" | grep -v grep """,
                                         ignore_failure=True)

        print "importing all gpg keys for yum repositories"
        self.ssh_client.run_command("rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-*")

        monitor = threading.Thread(target=monitor_yum)
        monitor.start()
        print "initiating yum update"
        self.ssh_client.run_command("yum update -y")

    def stop_cfme(self):
        print "stopping the cfme engine (evmserverd)"

        result = self.exec_commaned("systemctl status evmserverd | "
                                    "grep Active: | awk {'print $2'}", ignore_failure=True)

        if "active" in result.output:
            self.exec_commaned("systemctl stop evmserverd")

    def start_cfme(self):

        print "starting the cfme engine (evmserverd)"
        result = self.exec_commaned("systemctl status evmserverd | grep Active: | awk {'print $2'}",
                                    ignore_failure=True)

        if "inactive" in result.output:
            self.exec_commaned("systemctl start evmserverd")

    def yum_register(self, username, password):
        self.exec_commaned("subscription-manager register --username={username} "
                           "--password={password} "
                           "--force".format(username=username, password=password))

    def validate_cfme_version(self):
        print "waiting for 120 seconds for main proccess to load before runnig verrsion valiadation"
        time.sleep(120)
        print "start CFME version validation"
        api_url = "https://{ip}/api/".format(ip=self.address)
        auth = ("admin", "smartvm")
        si = requests.get(api_url, verify=False, auth=auth).json()["server_info"]
        assert si['version'].split("-", 1)[0] == self.dest_version, "The upgrade filed!"
        print "The upgrade finished successfully"

    def restart_components(self):
        print "restarting componates after updating components"

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

    print "loading config file"
    with open(args.config, 'r') as stream:
        try:
            params = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

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
                       "dest_version": {"msg": "destination version is missing",
                                        "is_mandatory": params.get("skip_validation", True),
                                        "default": None},
                       "repo": {"msg": "repolist is missing",
                                "is_mandatory": True, "default": None}}
    for key in requierd_fildes:
        if key not in params:
            if requierd_fildes[key]["is_mandatory"]:
                raise RuntimeError(requierd_fildes.get(key).get("msg"))
            else:
                print
                params.update({key: requierd_fildes.get(key).get("default")})

    print "Starting system upgrade"
    cfme_upgrader = cfme_upgrade_maneger(params["address"],
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
