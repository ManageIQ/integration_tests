# Our custom docker image with app
FROM patchkez/cfme_tests_base
MAINTAINER <RH>

LABEL company="Redhat" product="CFME" environment="dev" tier="test"

RUN pip install -U pip && pip install -U virtualenv

ENV PROJECTS /projects 

ENV CFMEENV cfme_env

ENV WORK $PROJECTS/$CFMEENV 

RUN mkdir $PROJECTS && cd $PROJECTS

# VOLUME /mnt/data/dock_vm_images/docker_volumes/rh_cfme_tests:$PROJECTS

WORKDIR $PROJECTS

RUN virtualenv $CFMEENV

WORKDIR $CFMEENV

RUN echo "export PYTHONPATH=$WORK/:${PYTHONPATH}" >> ~/.bashrc

RUN echo "source $WORK/bin/activate" >> ~/.bashrc

RUN echo "cd $WORK" >> ~/.bashrc

RUN echo "export CFME_ENV=$WORK" >> ~/.bashrc

RUN echo "export PYTHONPATH=${PYTHON_PATH}:$WORK/cfme_tests" >> bin/activate

RUN echo "PYTHONDONTWRITEBYTECODE=\"yes\"" >> bin/activate

RUN export PYCURL_SSL_LIBRARY=nss

RUN pip install -Ur https://raw.githubusercontent.com/RedHatQE/cfme_tests/master/requirements.txt && rm -rf ~/.cache/pip

RUN mkdir selenium; cd selenium; curl -L http://goo.gl/yLJLZg > selenium_latest.jar

RUN mkdir ~/.vnc

ADD xstartup /root/.vnc/xstartup

RUN chmod 755 /root/.vnc/xstartup

EXPOSE 5999 

CMD vncserver :99 -SecurityTypes None
