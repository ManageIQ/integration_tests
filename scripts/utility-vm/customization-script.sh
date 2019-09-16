#!/bin/bash

set -x -e

SHARE_PASSWORD="$1"

if [ -z "${SHARE_PASSWORD}" ]; then
    echo "Please supply a SHARE_PASSWORD as first argument to $0" >&2
    exit 1
fi

function rhel7y {
    RHEL_7_Y_IDENTIFIER="Red Hat Enterprise Linux Server release 7\.. .* (Maipo)"
    grep -q "$RHEL_7_Y_IDENTIFIER" /etc/redhat-release
}

function rhel8y {
    RHEL_8_Y_IDENTIFIER="Red Hat Enterprise Linux release 8\.. .* (Ootpa)"
    grep -q "$RHEL_8_Y_IDENTIFIER" /etc/redhat-release
}

sed -i'.orig' -e's/without-password/yes/' /etc/ssh/sshd_config

rhel7y && mv /tmp/rhel7.repo /etc/yum.repos.d/rhel.repo
rhel8y && mv /tmp/rhel8.repo /etc/yum.repos.d/rhel.repo

yum install -y nfs-utils samba vsftpd

# Create FS with little free space
truncate -s 3M /srv/littlespace
mkfs.ext2 /srv/littlespace
echo /srv/littlespace /srv/export/littlespacedir/ ext2 defaults 0 0 >> /etc/fstab
mkdir -p /srv/export/littlespacedir
mount -a
chown nobody:nobody /srv/export/littlespacedir
chmod u+w /srv/export/littlespacedir

# NFS setup
mkdir -p /srv/export
chmod a=rwx /srv/export
echo "/srv/export *(rw,crossmnt)" >> /etc/exports
rhel7y && ( systemctl enable nfs; systemctl start nfs )
rhel8y && ( systemctl enable nfs-server; systemctl start nfs-server )

# SMB setup
adduser backuper
echo -e "${SHARE_PASSWORD}\n${SHARE_PASSWORD}" | smbpasswd -sa backuper
mkdir -p /srv/samba
chmod a=rwx /srv/samba

cat >> /etc/samba/smb.conf <<EOF
[public]
comment = Public Stuff
path = /srv/samba
public = yes
writable = yes
printable = no
write list = +staff
EOF

systemctl enable smb
systemctl start smb

# FTP setup
systemctl enable vsftpd
systemctl start vsftpd
echo "${SHARE_PASSWORD}" | passwd --stdin backuper

# Prepare squid
yum -y install squid
systemctl enable squid

# Turn selinux off
sed  -i 's/SELINUX=.*/SELINUX=permissive/' /etc/selinux/config

touch /.unconfigured
