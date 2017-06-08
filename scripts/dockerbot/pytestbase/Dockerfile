FROM fedora:25
RUN dnf install -y \
		gcc postgresql-devel libxml2-devel libxslt-devel zeromq3-devel git nano python-devel gnupg gnupg2 \
		libcurl-devel redhat-rpm-config findutils libffi-devel openssl-devel python-virtualenv && dnf clean all

RUN git config --global user.email "me@dockerbot" && git config --global user.name "DockerBot"

RUN git clone https://github.com/ManageIQ/integration_tests
RUN cd /integration_tests && \
	python -m cfme.scripting.quickstart && \
	python -m cfme.scripting.quickstart --mk-virtualenv ../cfme_pristine_venv
ADD setup.sh /setup.sh
ADD post_result.py /post_result.py
ADD get_keys.py /get_keys.py
ADD verify_commit.py /verify_commit.py
RUN mkdir /log_depot

VOLUME ["/log_depot"]
WORKDIR /integration_tests
ENTRYPOINT ["bash", "/setup.sh"]