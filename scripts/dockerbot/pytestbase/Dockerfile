FROM fedora:21
RUN yum install -y gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel git nano python-devel gnupg gnupg2 libcurl-devel
RUN git clone https://github.com/RedHatQE/cfme_tests.git
RUN yum -y install python-setuptools; easy_install pip
RUN pip install -U -r /cfme_tests/requirements.txt
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py
ADD get_keys.py /get_keys.py
ADD verify_commit.py /verify_commit.py