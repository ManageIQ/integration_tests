FROM fedora:27

RUN dnf install -y gcc postgresql-devel libxml2-devel libxslt-devel zeromq-devel git nano python-devel gnupg gnupg2 libcurl-devel redhat-rpm-config findutils libffi-devel openssl-devel tesseract freetype-devel gcc-c++ python-pip libjpeg-devel iputils && dnf clean all
ARG CFME_REPO=https://github.com/RedHatQE/cfme_tests.git
ARG CFME_BRANCH=master
RUN git clone -b $CFME_BRANCH $CFME_REPO /cfme_tests
RUN cd /cfme_tests && PYCURL_SSL_LIBRARY=openssl pip install -U -r /cfme_tests/requirements/frozen.txt --no-cache-dir
RUN python -c 'import pycurl'
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py
ADD get_keys.py /get_keys.py
ADD verify_commit.py /verify_commit.py
ADD check_provisioned.py /check_provisioned.py
