# integration_tests
# FROM redhatqe/integration_tests_base
FROM patchkez/cfme_tests_test_base
MAINTAINER <RH>

LABEL company="Redhat" product="CFME" environment="dev" tier="test"

RUN pip install -U pip && pip install -U virtualenv

# This dir will contain all volumes and virtual environments
ENV PROJECTS /projects

# This is how our python venv will be called
ENV ENV_NAME cfme_env

ENV CFME_ENV $PROJECTS/$ENV_NAME

RUN mkdir -p $PROJECTS

WORKDIR $PROJECTS

RUN virtualenv $ENV_NAME

# Create directory under we mount all volumes
RUN mkdir -p cfme_vol

ENV CFME_VOL ${PROJECTS}/cfme_vol/

RUN echo "export PYTHONPATH=$CFME_ENV/:${PYTHONPATH}" >> /etc/bashrc && \
    echo "source $CFME_ENV/bin/activate" >> /etc/bashrc && \
    echo "cd $CFME_VOL/integration_tests" >> /etc/bashrc && \
    echo "export CFME_ENV=$CFME_ENV" >> /etc/bashrc && \
    echo "export PYTHONDONTWRITEBYTECODE=1" >> ${CFME_ENV}/bin/activate

# RUN echo "export PYTHONPATH=${PYTHON_PATH}:$WORK/cfme_vol/integration_tests" >> bin/activate

RUN export PYCURL_SSL_LIBRARY=nss && find . -iname "*.pyc" -exec rm '{}' \;

RUN curl -L  https://raw.githubusercontent.com/ManageIQ/integration_tests/master/requirements/frozen.py2.txt > requirements.txt && \
    source /root/.bashrc; PYCURL_SSL_LIBRARY=nss pip install -Ur ./requirements.txt \
    --no-binary numpy --no-binary matplotlib && pip install pudb pytest-pudb && \
    rm -rf ~/.cache/pip

RUN find . -name \*.pyc -delete && find . -name __pycache__ -delete

# Enable repo for google chrome
ADD google-chrome.repo /etc/yum.repos.d/

# ===== CHROME
ENV CHROME_PATH /opt/google/chrome
#RUN dnf install -y google-chrome-stable
# Workaround - above repo does not work?
RUN dnf install -y https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
#ADD http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
#    /root/chrome_webdriver/chromedriver_linux64.zip

# ===== CHROME DRIVER
ENV CHROME_DRIVER_VERSION 2.35
ENV CHROMEDRIVER_PATH /opt/chromedriver/
RUN mkdir -p ${CHROMEDRIVER_PATH} && cd ${CHROMEDRIVER_PATH} && \
    curl -O http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip && \
    unzip ./chromedriver_linux64.zip && \
    chmod a+x ${CHROMEDRIVER_PATH}/chromedriver && \
    rm -f ${CHROMEDRIVER_PATH}/chromedriver_linux64.zip

# ===== SELENIUM
# ENV SELENIUM_VERSION 2.53
ENV SELENIUM_VERSION 3.10
ENV SELENIUM_PATH /opt/selenium
# selenium
#ADD http://selenium-release.storage.googleapis.com/$SELENIUM_VERSION/selenium-server-standalone-$SELENIUM_VERSION.0.jar selenium/selenium_latest.jar
RUN mkdir -p ${SELENIUM_PATH} && cd ${SELENIUM_PATH} && \
    curl http://selenium-release.storage.googleapis.com/$SELENIUM_VERSION/selenium-server-standalone-$SELENIUM_VERSION.0.jar \
    -o selenium_latest.jar && chmod ugo+r selenium_latest.jar

# ===== FIREFOX
# firefox - esr
#ADD https://download-installer.cdn.mozilla.net/pub/firefox/releases/$FIREFOX_VERSION.0esr/linux-x86_64/en-US/firefox-$FIREFOX_VERSION.0esr.tar.bz2 \
# ENV FIREFOX_VERSION 38.6
# ENV FIREFOX_VERSION 47.0.2
ENV FIREFOX_VERSION 46.0.1
ENV FIREFOX_PATH /opt/firefox
RUN mkdir -p ${FIREFOX_PATH} && cd ${FIREFOX_PATH} && \
    curl https://download-installer.cdn.mozilla.net/pub/firefox/releases/$FIREFOX_VERSION/linux-x86_64/en-US/firefox-$FIREFOX_VERSION.tar.bz2 \
    -o firefox.tar.bz2 && tar -C ${FIREFOX_PATH} -xjvf ${FIREFOX_PATH}/firefox.tar.bz2 --strip-components 1 && \
    rm -f ${FIREFOX_PATH}/firefox.tar.bz2
# RUN tar -C $FIREFOX_PATH -xjvf /root/firefox.tar.bz2 && rm -f /root/firefox.tar.bz2

RUN mkdir -p ~/.vnc && uuidgen | sed 's/-//g' > /etc/machine-id

# setup firefox and chrome paths
ENV PATH="${FIREFOX_PATH}:${CHROME_PATH}:${CHROMEDRIVER_PATH}:${SELENIUM_PATH}:${PATH}"

ADD xstartup /usr/local/bin/xstartup

EXPOSE 5999 

# ADD ./entry.sh /entry.sh

# ENTRYPOINT ["/entry.sh"]
 
# RUN echo "ALL ALL=NOPASSWD: /projects/cfme_env/bin/pip install -e ." >> /etc/sudoers

RUN chmod a+w ${CFME_ENV}/lib/python2.7/site-packages/
RUN chmod a+w ${CFME_ENV}/bin

CMD useradd ${USERNAME} -g ${GOUP_ID} -M -u ${USER_ID} && \
    vncserver :99 -xstartup /usr/local/bin/xstartup -SecurityTypes None && \
    tail -F ~/.vnc/*.log
