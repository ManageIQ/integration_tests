FROM fedora:28
ARG GIT_REPO=https://github.com/Manageiq/integration_tests
ARG GIT_BRANCH=master

# this can be dropped after the python3 switch
RUN dnf update -y && dnf install -y python2 'dnf-command(debuginfo-install)'

WORKDIR /integration_tests
COPY cfme/scripting/ cfme/scripting/
COPY cfme/__init__.py cfme/__init__.py
COPY requirements requirements
COPY setup.py setup.py
RUN mkdir conf
RUN python -m cfme.scripting.quickstart --mk-virtualenv /cfme_venf



RUN dnf install -y git
RUN git config --global user.name DockerCfme
run git config --global user.email no-reply@unused.example.redhat.com


COPY . .
COPY .git .git

RUN git remote add docker-upstream ${GIT_REPO}
RUN git fetch -a --tags || echo ignored if missing
RUN git fetch upstream -a --tags || echo not having upstream is fine
RUN git fetch docker-upstream -a --tags || echo not having docker-upstream is fine as well
