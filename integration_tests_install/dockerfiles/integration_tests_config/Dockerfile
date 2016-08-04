# integration_tests_config

#FROM redhatqe/integration_tests_base
FROM patchkez/cfme_tests_test_base

MAINTAINER <RH>

LABEL company="Redhat" product="Ansible" environment="dev" tier="test"

RUN easy_install pip

RUN pip install virtualenv os-client-config shade ipython

ENV PROJECTS /projects 

ENV PROJENV ansible_virtenv

ENV REPO ansible_work

ENV WORK $PROJECTS/$PROJENV 

RUN mkdir -p $PROJECTS && cd $PROJECTS

WORKDIR $PROJECTS

RUN virtualenv $PROJENV

WORKDIR $PROJENV

RUN git clone git://github.com/ansible/ansible.git --recursive

RUN mkdir -p $REPO

VOLUME /var/tmp/repo:/projects/ansible_virtenv/ansible_work

RUN echo "source $WORK/bin/activate" >> ~/.bashrc

RUN echo "cd $WORK/ansible_work" >> ~/.bashrc

RUN echo "source $WORK/ansible/hacking/env-setup" >> ~/.bashrc

RUN . $WORK/bin/activate; pip install -U virtualenv paramiko PyYAML Jinja2 httplib2 pycrypto netaddr

RUN uuidgen | sed 's/-//g' > /etc/machine-id

CMD /bin/bash -l -c "ansible-playbook -i inventory -c local configure_integration_tests.yml"
