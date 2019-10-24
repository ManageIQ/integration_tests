import hashlib
import re
from functools import wraps

import fauxfactory
import iso8601
from celery import shared_task
from django.core.cache import cache

from appliances.models import Template
from sprout import settings
from sprout.log import create_logger

LOCK_EXPIRE = 60 * 15  # 15 minutes


def docker_vm_name(version, date):
    return 'docker-{}-{}-{}'.format(
        re.sub(r'[^0-9a-z]', '', version.lower()),
        re.sub(r'[^0-9]', '', str(date)),
        fauxfactory.gen_alphanumeric(length=4).lower())


def parsedate(d):
    if d is None:
        return d
    else:
        return iso8601.parse_date(d)


def singleton_task(*args, **kwargs):
    kwargs["bind"] = True
    wait = kwargs.pop('wait', False)
    wait_countdown = kwargs.pop('wait_countdown', 10)
    wait_retries = kwargs.pop('wait_retries', 30)

    def f(task):
        @wraps(task)
        def wrapped_task(self, *args, **kwargs):
            self.logger = create_logger(task)
            # Create hash of all args
            digest_base = "/".join(str(arg) for arg in args)
            keys = sorted(kwargs.keys())
            digest_base += "//" + "/".join("{}={}".format(key, kwargs[key]) for key in keys)
            digest = hashlib.sha256(digest_base.encode('utf-8')).hexdigest()
            lock_id = '{0}-lock-{1}'.format(self.name, digest)

            if cache.add(lock_id, 'true', LOCK_EXPIRE):
                try:
                    return task(self, *args, **kwargs)
                except Exception as e:
                    self.logger.error(
                        "An exception occured when executing with args: %r kwargs: %r",
                        args, kwargs)
                    self.logger.exception(e)
                    raise
                finally:
                    cache.delete(lock_id)
            elif wait:
                self.logger.info("Waiting for another instance of the task to end.")
                self.retry(args=args, countdown=wait_countdown, max_retries=wait_retries)

        return shared_task(*args, **kwargs)(wrapped_task)

    return f


def logged_task(*args, **kwargs):
    new_kwargs = kwargs.copy()
    new_kwargs["bind"] = True

    def f(task):
        @wraps(task)
        def wrapped_task(self, *args, **kwargs):
            self.logger = create_logger(task)
            try:
                return task(self, *args, **kwargs)
            except Exception as e:
                self.logger.error(
                    "An exception occured when executing with args: %r kwargs: %r",
                    args, kwargs)
                self.logger.exception(e)
                raise

        return shared_task(*args, **new_kwargs)(wrapped_task)

    return f


def provider_error_logger():
    return create_logger("provider_errors")


def gen_appliance_name(template_id, username=None):
    template = Template.objects.get(id=template_id)
    if template.template_type != Template.OPENSHIFT_POD:
        appliance_format = settings.APPLIANCE_FORMAT
    else:
        appliance_format = settings.OPENSHIFT_APPLIANCE_FORMAT

    new_appliance_name = appliance_format.format(
        group=template.template_group.id,
        date=template.date.strftime("%y%m%d"),
        rnd=fauxfactory.gen_alphanumeric(8).lower())

    # Apply also username
    if username:
        new_appliance_name = "{}_{}".format(username, new_appliance_name)
        if template.template_type == Template.OPENSHIFT_POD:
            # openshift doesn't allow underscores to be used in project names
            new_appliance_name = new_appliance_name.replace('_', '-')
    return new_appliance_name
