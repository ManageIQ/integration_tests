# integration_tests_base

FROM fedora:23

MAINTAINER <RH>

LABEL company="Redhat" product="ManageIQ/CFME" environment="dev" tier="test"

# Add Chrome repo
RUN echo $'[google-chrome] \n\
name=google-chrome - \$basearch \n\
baseurl=http://dl.google.com/linux/chrome/rpm/stable/\$basearch \n\
enabled=1 \n\
gpgcheck=1 \n\
gpgkey=https://dl-ssl.google.com/linux/linux_signing_key.pub' > /etc/yum.repos.d/google-chrome.repo

# mandatory packages
RUN dnf -y install http://linuxdownload.adobe.com/linux/x86_64/adobe-release-x86_64-1.0-1.noarch.rpm && \
    rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-adobe-linux && \
    dnf -y install which git python-pip gcc gcc-c++ postgresql-devel libxml2-devel libxslt-devel zeromq3-devel libcurl-devel python-devel redhat-rpm-config libffi-devel openssl-devel \
    tigervnc-server fluxbox xterm java-1.8.0-openjdk.x86_64 flash-plugin nspluginwrapper unzip xorg-x11-fonts-* dejavu* bzip2\
    ftp://rpmfind.net/linux/fedora/linux/releases/22/Everything/x86_64/os/Packages/f/firefox-38.0.1-1.fc22.x86_64.rpm sudo\
    python-setuptools sshpass python-netaddr findutils \
   # autocutsel \
   # google-chrome-stable \
    && dnf clean all

# Setup Adobe Flash plugin
RUN mkdir -p /.mozilla/plugins && \
   ln -s /usr/lib64/flash-plugin/libflashplayer.so /.mozilla/plugins/libflashplayer.so && \
   sed -i 's#/dev/random#/dev/urandom#' /etc/alternatives/jre/lib/security/java.security

RUN uuidgen | sed 's/-//g' > /etc/machine-id
