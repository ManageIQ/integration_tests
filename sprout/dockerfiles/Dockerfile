FROM fedora:30

# installing essential packages
RUN dnf install -y git vim python3 python3-devel python3-pip python3-requests procps-ng iputils \
                   iproute git gcc libxml2-devel libxslt-devel libcurl-devel \
                   libpq-devel nginx redis && dnf clean all

RUN pip3 install -U pip && pip3 install -U virtualenv

EXPOSE 8000

# setup everything
ENV GIT_SSL_NO_VERIFY true

ENV PROJ /sprout
ENV SPROUT_DIR /$PROJ/sprout


# fixme: below
#RUN git clone https://github.com/ManageIQ/integration_tests.git $PROJ
#RUN git clone https://github.com/izapolsk/integration_tests.git $PROJ
ADD . $PROJ
WORKDIR $PROJ
#RUN git checkout py3-sprout

#WORKDIR $SPROUT_DIR

ENV VENV /venv
RUN python3 -m cfme.scripting.quickstart --mk-virtualenv $VENV


RUN umask 0000
RUN mkdir -p /run/gunicorn /var/log/gunicorn $PROJ/db
RUN chmod 777 $PROJ/db

#RUN  sed -i -- 's/types_hash_max_size.*;/types_hash_max_size 4096;/' /etc/nginx/nginx.conf && \
#     sed -i -- '/types_hash_max_size/a server_names_hash_bucket_size 128;' /etc/nginx/nginx.conf

# prepare config file and
RUN source $VENV/bin/activate; pip3 install -U -r $SPROUT_DIR/requirements.txt && \
    pip3 install gunicorn

RUN source $VENV/bin/activate; yes "yes" | python3 $SPROUT_DIR/manage.py collectstatic
#RUN source $VENV/bin/activate; python3 manage.py migrate

CMD source $VENV/bin/activate && python3 $SPROUT_DIR/manage.py runserver 0.0.0.0:8000
#CMD source $VENV/bin/activate; gunicorn -b unix:/run/gunicorn/trackerbot.sock -t 600 -w 4 -u root --error-logfile /var/log/gunicorn/trackerbot-error.log wsgi:application
