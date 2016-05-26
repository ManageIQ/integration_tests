# Our custom docker image with app
FROM fedora:23
MAINTAINER <RH>

LABEL company="Redhat" product="CFME" environment="dev" tier="test"

# mandatory packages
RUN dnf -y install git python-pip gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel python-devel redhat-rpm-config libffi-devel openssl-devel \
tigervnc-server fluxbox xterm java-1.8.0-openjdk.x86_64 \
ftp://rpmfind.net/linux/fedora/linux/releases/22/Everything/x86_64/os/Packages/f/firefox-38.0.1-1.fc22.x86_64.rpm \
python-setuptools sshpass findutils \
&& dnf clean all
