FROM fedora:30

RUN dnf install -y gcc postgresql-devel libxml2-devel libxslt-devel zeromq-devel git nano python3-devel gnupg gnupg2 libcurl-devel redhat-rpm-config findutils libffi-devel openssl-devel tesseract freetype-devel gcc-c++ python3-pip python3 libjpeg-devel iputils && dnf clean all
ARG CFME_REPO=https://github.com/ManageIQ/integration_tests.git
ARG CFME_BRANCH=master
RUN git clone -b $CFME_BRANCH $CFME_REPO /cfme_tests
RUN cd /cfme_tests && PYCURL_SSL_LIBRARY=openssl pip3 install -U -r /cfme_tests/requirements/frozen.py3.txt --no-cache-dir
RUN python3 -c 'import pycurl'
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py
ADD get_keys.py /get_keys.py
ADD verify_commit.py /verify_commit.py
ADD check_provisioned.py /check_provisioned.py
