FROM fedora:20
RUN yum install -y gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel git nano python-pip python-devel
RUN git clone https://github.com/RedHatQE/cfme_tests.git 
RUN pip install -U -r /cfme_tests/requirements.txt
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py