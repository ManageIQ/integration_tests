FROM registry.fedoraproject.org/fedora:26

ENV PYCURL_SSL_LIBRARY=nss
ENV PYTHONDONTWRITEBYTECODE=1
ENV CFME_ENV=/

RUN dnf install -y --setopt=tsflags=nodocs \
    # Base packages
    git \
    # For selenium xstartup script
    fluxbox \
    # Preloaded from cfme.scripting.quickstart
    openssh-server \
    python \
    tigervnc-server \
    freetype-devel \
    gcc \
    gcc-c++ \
    libcurl-devel \
    libffi-devel \
    libxml2-devel \
    libxslt-devel \
    openssl-devel \
    postgresql-devel \
    python2-devel \
    python2-virtualenv \
    redhat-rpm-config \
    tesseract \
    zeromq-devel \
    && dnf clean all

# Build and setup selenium
RUN mkdir /selenium; curl -L http://goo.gl/yLJLZg > /selenium/selenium_latest.jar
ADD dockerfiles/cfme_tests_img/xstartup /root/.vnc/xstartup
EXPOSE 5999

RUN virtualenv /cfme_venv
RUN echo "source /cfme_venv/bin/activate" >> /root/.bashrc

# Preinstall any python dependencies to keep it in an early layer
RUN curl https://raw.githubusercontent.com/ManageIQ/integration_tests/master/requirements/frozen.txt > frozen.txt
RUN ../cfme_venv/bin/pip install -U pip wheel setuptools_scm docutils
RUN ../cfme_venv/bin/pip install -r frozen.txt --no-binary pycurl --no-binary numpy --no-binary matplotlib
RUN ../cfme_venv/bin/python -c 'import curl'

# RUN git clone https://github.com/ManageIQ/integration_tests.git
RUN git clone https://github.com/psav/cfme_tests.git --branch dev_trial integration_tests
# RUN git clone https://github.com/ManageIQ/integration_tests.git
WORKDIR integration_tests

RUN touch .yaml_key
RUN mkdir -p ../cfme-qe-yamls/complete/

RUN python -m cfme.scripting.quickstart

# RUN cd conf && for file in $(ls); do cp $file ${file%.template}; done
ADD conf/*.yaml  /integration_tests/conf/

ADD docker-assets/entrypoint /entrypoint

ENTRYPOINT /entrypoint
