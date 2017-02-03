# integration_tests
# FROM redhatqe/integration_tests_base
FROM patchkez/cfme_tests_test_base
MAINTAINER <RH>

LABEL company="Redhat" product="CFME" environment="dev" tier="test"

RUN pip install -U pip && pip install -U virtualenv

ENV PROJECTS /projects 

ENV CFMEENV cfme_env

ENV WORK $PROJECTS/$CFMEENV 

RUN mkdir -p $PROJECTS && cd $PROJECTS

WORKDIR $PROJECTS

RUN virtualenv $CFMEENV

WORKDIR $CFMEENV

RUN mkdir -p cfme_vol

#RUN echo "export PYTHONPATH=$WORK/:${PYTHONPATH}" >> ~/.bashrc
RUN echo "export PYTHONPATH=$WORK/:${PYTHONPATH}" >> /etc/bashrc

#RUN echo "source $WORK/bin/activate" >> ~/.bashrc
RUN echo "source $WORK/bin/activate" >> /etc/bashrc

#RUN echo "cd $WORK" >> ~/.bashrc
RUN echo "cd $WORK/cfme_vol/integration_tests" >> /etc/bashrc

#RUN echo "export CFME_ENV=$WORK" >> ~/.bashrc
RUN echo "export CFME_ENV=$WORK" >> /etc/bashrc

RUN echo "export PYTHONPATH=${PYTHON_PATH}:$WORK/cfme_vol/integration_tests" >> bin/activate

RUN echo "PYTHONDONTWRITEBYTECODE=\"yes\"" >> bin/activate

RUN export PYCURL_SSL_LIBRARY=nss

RUN find . -iname "*.pyc" -exec rm '{}' \;

RUN curl -L  https://raw.githubusercontent.com/RedHatQE/cfme_tests/master/requirements.txt > requirements.txt

RUN sed -i '/-e \./d' requirements.txt

RUN source /root/.bashrc; PYCURL_SSL_LIBRARY=nss pip install -Ur ./requirements.txt && rm -rf ~/.cache/pip

# ENV CHROME_DRIVER_VERSION 2.21
ENV CHROME_DRIVER_VERSION 2.27
# ENV SELENIUM_VERSION 2.51
ENV SELENIUM_VERSION 2.53
ENV FIREFOX_VERSION 38.6

RUN dnf install -y google-chrome-stable

ADD http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    /root/chrome_webdriver/chromedriver_linux64.zip

RUN unzip /root/chrome_webdriver/chromedriver_linux64.zip -d bin/ && \
    chmod a+x bin/chromedriver && \
    rm -f /root/chrome_webdriver/chromedriver_linux64.zip

# selenium
ADD http://selenium-release.storage.googleapis.com/$SELENIUM_VERSION/selenium-server-standalone-$SELENIUM_VERSION.0.jar selenium/selenium_latest.jar

RUN chmod ugo+r selenium/selenium_latest.jar

# firefox
ADD https://download-installer.cdn.mozilla.net/pub/firefox/releases/$FIREFOX_VERSION.0esr/linux-x86_64/en-US/firefox-$FIREFOX_VERSION.0esr.tar.bz2 \
    /root/firefox.tar.bz2

RUN tar -C /root/ -xjvf /root/firefox.tar.bz2 && rm -f /root/firefox.tar.bz2

RUN mkdir -p ~/.vnc

ADD xstartup /usr/local/bin/xstartup

#RUN chmod 755 /root/.vnc/xstartup

RUN uuidgen | sed 's/-//g' > /etc/machine-id

EXPOSE 5999 

# ADD ./entry.sh /entry.sh

# ENTRYPOINT ["/entry.sh"]
 
CMD vncserver :99 -xstartup /usr/local/bin/xstartup -SecurityTypes None && tail -F ~/.vnc/*.log
