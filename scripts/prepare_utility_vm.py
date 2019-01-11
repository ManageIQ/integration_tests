from wrapanapi.systems.openstack import OpenstackSystem
from cfme.utils.conf import credentials, cfme_data
from textwrap import dedent
from cfme.utils.ssh import SSHClient


def create_utility_template(base_template, key):
    data = cfme_data[key]
    OpenstackSystem(
        tenant=data.credentials['tenant'],
        username=data.credentials['username'],
        password=data.credentials['password'],
        auth_url=data.auth_url)


def configure(hostname, username, password):
    connect_kwargs = {
        'hostname': hostname,
        'username': username,
        'password': password
    }
    setup = (
        # Common setup.
        dedent(''' \
        cat > /etc/yum.repos.d/rhel.repo <<EOF
        [rhel]
        name=RHEL 7.5-Update
        baseurl={baseurl}
        enabled=1
        gpgcheck=0
        skip_if_unavailable=False
        EOF
        ''').format(baseurl=cfme_data['basic_info']['rhel7_updates_url']),
        'yum install -y nfs-utils samba',
        'setenforce 0',

        # NFS setup
        'mkdir -p /srv/export',
        'chmod a=rwx /srv/export',
        'echo "/srv/export *(ro)" >> /etc/exports',
        'firewall-cmd --add-port=2049/udp --permanent',
        'firewall-cmd --add-port=2049/tcp --permanent',
        'firewall-cmd --add-port=111/udp --permanent',
        'firewall-cmd --add-port=111/tcp --permanent',
        'firewall-cmd --reload',
        'systemctl enable nfs',
        'systemctl start nfs',
        'exportfs -ra',

        # SMB setup
        'adduser backuper',
        #'smbpasswd -a backuper', # TODO(jhenner) set the password!
        'mkdir -p /srv/samba',
        'chmod a=rwx /srv/samba',
        'firewall-cmd --add-port=139/tcp --permanent',
        'firewall-cmd --add-port=445/tcp --permanent',
        'firewall-cmd --reload',
        dedent('''\
            cat >> /etc/samba/smb.conf <<EOF
            [public]
            comment = Public Stuff
            path = /srv/samba
            public = yes
            writable = no
            printable = no
            write list = +staff
            EOF
            '''),
        'systemctl enable smb',
        'systemctl start smb',
    )
    vm_ssh = SSHClient(**connect_kwargs)
    for line in setup:
        assert vm_ssh.run_command(line).success
