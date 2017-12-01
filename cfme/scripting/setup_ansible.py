# -*- coding: utf-8 -*-
import requests

from cfme.utils import ports
from cfme.utils.net import net_check
from cfme.utils.wait import wait_for


ANSIBLE_TOWER_REPO_PATH = "/etc/yum.repos.d/ansible-tower.repo"
ANSIBLE_TOWER_REPO_CONTENT = """EOF
[ansible-tower]
name=Ansible Tower Repository - $releasever $basearch
baseurl=http://releases.ansible.com/ansible-tower/rpm/epel-7-\$basearch
enabled=1
gpgcheck=0
EOF"""
JLASKA_RABBITMQ_REPO_PATH = "/etc/yum.repos.d/jlaska-rabbitmq.repo"
JLASKA_RABBITMQ_REPO_CONTENT = """EOF
[jlaska-rabbitmq]
name=Copr repo for rabbitmq owned by jlaska
baseurl=https://copr-be.cloud.fedoraproject.org/results/jlaska/rabbitmq/epel-7-\$basearch/
skip_if_unavailable=True
gpgcheck=1
gpgkey=https://copr-be.cloud.fedoraproject.org/results/jlaska/rabbitmq/pubkey.gpg
enabled=1
enabled_metadata=1
EOF"""
PGDG_96_CENTOS_REPO_PATH = "/etc/yum.repos.d/pgdg-96-centos.repo"
PGDG_96_CENTOS_REPO_CONTENT = """EOF
[pgdg96]
name=PostgreSQL 9.6 $releasever - $basearch
baseurl=http://download.postgresql.org/pub/repos/yum/9.6/redhat/rhel-\$releasever-\$basearch
enabled=1
gpgcheck=0
EOF"""
REPOS = [
    (ANSIBLE_TOWER_REPO_PATH, ANSIBLE_TOWER_REPO_CONTENT),
    (JLASKA_RABBITMQ_REPO_PATH, JLASKA_RABBITMQ_REPO_CONTENT),
    (PGDG_96_CENTOS_REPO_PATH, PGDG_96_CENTOS_REPO_CONTENT)
]


def run_command(app, command):
    print(command)
    app.ssh_client.run_command(command)


def setup_repos(app):
    print("Starting configuring repos")
    for path, content in REPOS:
        run_command(app, "cat > {path} << {content}".format(path=path, content=content))


def install_packages(app):
    print("Starting to install packages")
    run_command(app, "yum -y install ansible-tower-setup ansible-tower-server")
    run_command(app, "install -o awx -g awx -m 0755 -d /var/log/tower")
    run_command(app, "install -o awx -g awx -m 0644 /dev/null /var/log/tower/callback_receiver.log")
    run_command(app, "install -o awx -g awx -m 0644 /dev/null /var/log/tower/fact_receiver.log")
    run_command(app, "install -o awx -g awx -m 0644 /dev/null /var/log/tower/task_system.log")
    run_command(app, "install -o awx -g awx -m 0644 /dev/null /var/log/tower/tower.log")
    run_command(app,
        "install -o awx -g awx -m 0644 /dev/null /var/log/tower/tower_rbac_migrations.log")
    run_command(app,
        "install -o awx -g awx -m 0644 /dev/null /var/log/tower/tower_system_track_migrations.log")
    run_command(app,
        "install -o awx -g awx -m 0644 /dev/null "
        "/var/log/tower/tower_system_tracking_migrations.log")


def get_ansible_password(app):
    print("Getting embedded ansible password. It can take a long time.")
    app.ssh_client.run_rails_command("'EmbeddedAnsible.start'")
    return app.ssh_client.run_rails_command(
        "'puts MiqDatabase.first.ansible_admin_authentication.password'").output.rstrip()


def open_port(app):
    run_command(app, "firewall-cmd --zone manageiq --add-port {}/tcp".format(ports.TOWER))
    print("Waiting until port {} will be opened".format(ports.TOWER))
    wait_for(
        net_check,
        [ports.TOWER, app.hostname],
        {"force": True},
        num_sec=600,
        delay=5
    )


def upload_license(app, license_path):
    password = get_ansible_password(app)
    print("Password is {}".format(password))
    open_port(app)
    print("Sending license file to embedded ansible")
    r = requests.post(
        'https://{addr}:{port}/api/v1/config/'.format(addr=app.hostname, port=ports.TOWER),
        headers={"Content-Type": "application/json"},
        data=open(license_path, "rb"),
        auth=("admin", password),
        verify=False
    )
    if r.status_code == 200:
        print("The license has been accepted.")
    else:
        print("Error occured: '{}'".format(r.json()["detail"]))


def stop_embedded_ansible(app):
    print("Stopping embedded ansible")
    app.ssh_client.run_rails_command("'EmbeddedAnsible.stop'")


def setup_ansible(app, license_path):
    setup_repos(app)
    install_packages(app)
    upload_license(app, license_path)
    stop_embedded_ansible(app)
