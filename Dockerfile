FROM registry.fedoraproject.org/fedora:26

RUN echo "tsflags=nodocs" >> /etc/yum.conf

COPY docker-assets/google-chrome.repo /etc/yum.repos.d/

RUN dnf install -y http://linuxdownload.adobe.com/linux/x86_64/adobe-release-x86_64-1.0-1.noarch.rpm && \
    rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-adobe-linux && \
    dnf install -y \
    # Base packages
    bzip2 \
    dejavu* \
    findutils \
    flash-plugin \
    fluxbox \
    freetype-devel \
    gcc \
    gcc-c++ \
    git \
    gtk2 \
    java-1.8.0-openjdk.x86_64 \
    libcurl-devel \
    libffi-devel \
    libpng-devel \
    libxml2-devel \
    libxslt-devel \
    openssl-devel \
    passwd \
    postgresql-devel \
    python-devel \
    python-netaddr \
    python-pip \
    python-setuptools \
    python2-virtualenv \
    redhat-rpm-config \
    sshpass \
    sudo \
    tigervnc-server \
    unzip \
    which \
    xorg-x11-fonts-* \
    xterm \
    zeromq-devel && \
    dnf install -y https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm && \
    dnf clean all

ENV CHROME_PATH /opt/google/chrome
ENV CHROMEDRIVER_VERSION 2.35
ENV CHROMEDRIVER_PATH /opt/chromedriver/
ENV SELENIUM_VERSION 2.53
ENV SELENIUM_PATH /opt/selenium
ENV FIREFOX_VERSION 45.5.0esr
ENV FIREFOX_PATH /opt/firefox

# Chrome driver
RUN mkdir -p ${CHROMEDRIVER_PATH} && \
    cd ${CHROMEDRIVER_PATH} && \
    curl -O http://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    chmod a+x chromedriver && \
    rm -f chromedriver_linux64.zip

# Selenium
RUN mkdir -p ${SELENIUM_PATH} && \
    cd ${SELENIUM_PATH} && \
    curl http://selenium-release.storage.googleapis.com/${SELENIUM_VERSION}/selenium-server-standalone-${SELENIUM_VERSION}.0.jar -o selenium_latest.jar && \
    chmod ugo+r selenium_latest.jar
EXPOSE 5999

# Firefox
RUN mkdir -p ${FIREFOX_PATH} && \
    cd ${FIREFOX_PATH} && \
    curl https://download-installer.cdn.mozilla.net/pub/firefox/releases/${FIREFOX_VERSION}/linux-x86_64/en-US/firefox-${FIREFOX_VERSION}.tar.bz2 -o firefox.tar.bz2 && \
    tar -C . -xjvf firefox.tar.bz2 --strip-components 1 && \
    rm -f firefox.tar.bz2

ENV PATH="${FIREFOX_PATH}:${CHROME_PATH}:${CHROMEDRIVER_PATH}:${SELENIUM_PATH}:${PATH}"

ENV PYCURL_SSL_LIBRARY=nss
ENV PYTHONDONTWRITEBYTECODE=1
ENV CFME_ENV=/

RUN virtualenv /cfme_venv
RUN echo "source /cfme_venv/bin/activate" >> /root/.bashrc

# Preinstall any python dependencies to keep it in an early layer
COPY requirements/frozen.py2.txt frozen.py2.txt
RUN /cfme_venv/bin/pip install --no-cache-dir -U pip wheel setuptools_scm docutils && \
    /cfme_venv/bin/pip install --no-cache-dir -r frozen.py2.txt --no-binary pycurl && \
    rm -rf ~/.cache/pip && \
    find . -name *.pyc -delete && \
    find . -name __pycache__ -delete

VOLUME /projects/cfme_env/cfme_vol
WORKDIR /projects/cfme_env/cfme_vol

COPY docker-assets/xstartup /xstartup
COPY docker-assets/entrypoint /entrypoint

ENTRYPOINT ["/entrypoint"]
