# Intended build context is integration_tests top level

FROM dima-sel-base:latest

ENV PYCURL_SSL_LIBRARY=nss \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV=/cfme_venv \
    CFME_ENV=/integration_tests

COPY ./cfme/scripting $CFME_ENV/cfme/scripting/
COPY ./requirements.txt $CFME_ENV/
COPY requirements/ $CFME_ENV/
WORKDIR $CFME_ENV
# for package installs through quickstart
USER 0
RUN python2 -m cfme.scripting.quickstart --mk-virtualenv $VENV
RUN source $VENV/bin/activate && pip freeze && pip install -e .

# integration_tests volume mounted at run time to pickup real-time changes
VOLUME $CFME_ENV
WORKDIR $CFME_ENV

COPY ./dockerfiles/cfme_tests_dev/docker-assets/entrypoint /entrypoint

EXPOSE 5999

ENTRYPOINT ["/entrypoint"]
