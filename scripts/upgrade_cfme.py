import argparse
import yaml
import copy

from utils.appliance import IPAppliance


class cfme_upgrade_maneger(IPAppliance):

    def __init__(self, appliance_ip, repo_list):
        super(cfme_upgrade_maneger, self).__init__(address=appliance_ip)
        self.repo_list = repo_list

    def add_yum_repo(self):

        for curr_repo_url in self.repo_list:
            # Add all the repos to yum repo
            result = self.ssh_client.run_command("yum-config-manager --add-repo {repo_url}".format(repo_url=curr_repo_url))

            # Validate repo added sussefully
            if not result.rc:
                print "Fail to add {repo_name} to yum repo list".format(repo_name=curr_repo_url)
            else:
                print"repo {repo_name} added succsefully".format(repo_name=curr_repo_url)

            print result.output

    def update_yum(self):

        print "=== Initiating yum update ======================================="
        self.ssh_client.run_command("rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-*")

        status, out = self.ssh_client.run_command("yum update -y")
        if status:
            print "rpm updating failed\n\n error log:\n"
            print out
        else:
            print "rpm updating succeeded!"
        print "================================================================="

    def stop_cfme(self):
        print "=== stopping the cfme engine (evmserverd) ======================="

        result = self.ssh_client.run_command("systemctl stop evmserverd")
        if not result.rc:
            result = self.ssh_client.run_command("systemctl status evmserverd | grep Active: | awk {'print $2'}")
            if "inactive" not in result.output:
                raise RuntimeError( "Fail to stop cfme engine")
        print result.output
        print "================================================================="

    def start_cfme(self):
        print "=== starting the cfme engine (evmserverd) ======================="

        result = self.ssh_client.run_command("systemctl start evmserverd")
        if not result.rc:
            result = self.ssh_client.run_command("systemctl status evmserverd | grep Active: | awk {'print $2'}")
            if "inactive" not in result.output:
                raise RuntimeError("Fail to stop cfme engine")
        print result.output
        print "================================================================="

    def yum_register(self ,username ,password):
        result = self.ssh_client.run_command(
            "subscription-manager register --username={username} --password={password} --force".format(
                username=username, password=password))
        if result.rc:
            raise RuntimeError(
                "yum fail to register with {username}:{password}\n\nfull error details:\n{full_error}".format(
                    username=username, password=password, full_error=result.output))

    def validate_cfme_version(self):
        pass

    def restart_components(self):
        self.ssh_client.run_command("systemctl restart $APPLIANCE_PG_SERVICE")
        self.ssh_client.run_rake_command("db:migrate")
        self.ssh_client.run_rake_command("evm:automate:reset")
        self.ssh_client.run_rake_command("systemctl restart $APPLIANCE_PG_SERVICE")

def main():
    parser = argparse.ArgumentParser(epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-a",'--address', dest="address", action="store", help='hostname or ip address of target appliance')
    parser.add_argument("-r", "--repo", help="url for yum repo with the relevant rpm", dest="repo", action="append")
    parser.add_argument("-c", "--config", help="yaml file with configurtations", dest="config", action="store", default=False)
    parser.add_argument("-u", "--username", help="username for yum register default:qa@redhat.com", dest="username", action="store", default="qa@redhat.com")
    parser.add_argument("-p", "--password", help="password for yum register", dest="password", action="store")
    args = parser.parse_args()

    params = {}
    if args.config:
        with open(args.config, 'r') as stream:
            try:
                params = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
    else:
        params = copy.deepcopy(args.__dict__)

    cfme_upgrader = cfme_upgrade_maneger(params["address"], repo_list=params["repo"])


    cfme_upgrader.add_yum_repo()
    cfme_upgrader.stop_cfme()
    cfme_upgrader.yum_register(params["username"], params["password"])
    cfme_upgrader.update_yum()
    cfme_upgrader.restart_components()
    cfme_upgrader.start_cfme()

if __name__ == '__main__':
    main()
