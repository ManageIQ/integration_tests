FROM fedora:20
RUN yum install -y gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel git nano python-pip python-devel gnupg gnupg2
RUN git clone https://github.com/RedHatQE/cfme_tests.git 
RUN pip install -U -r /cfme_tests/requirements.txt
RUN yum -y install https://kojipkgs.fedoraproject.org//packages/git/2.1.0/1.fc21/x86_64/git-2.1.0-1.fc21.x86_64.rpm git.rpm https://kojipkgs.fedoraproject.org//packages/git/2.1.0/1.fc21/noarch/perl-Git-2.1.0-1.fc21.noarch.rpm
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py
ADD get_keys.py /get_keys.py
ADD verify_commit.py /verify_commit.py