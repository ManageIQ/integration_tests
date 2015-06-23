# -*- coding: utf-8 -*-
from __future__ import absolute_import
from contextlib import contextmanager
try:
    import cPickle as pickle
except ImportError:
    import pickle
from .celery import app as celery_app
assert celery_app

from django.core.cache import cache
from sprout import settings
from redis import StrictRedis
from utils.path import project_path
from utils.wait import wait_for

redis_client = StrictRedis(**settings.GENERAL_REDIS)


CRITICAL_SECTION_LOCK_TIME = 60


@contextmanager
def critical_section(name):
    wait_for(
        cache.add,
        ["lock-{}".format(name), 'true', CRITICAL_SECTION_LOCK_TIME],
        delay=0.3, num_sec=2 * CRITICAL_SECTION_LOCK_TIME)
    try:
        yield
    finally:
        cache.delete("lock-{}".format(name))


class RedisWrapper(object):
    LOCK_EXPIRE = 60

    def __init__(self, client):
        self.client = client

    def _set(self, key, value, *args, **kwargs):
        return self.client.set(str(key), pickle.dumps(value), *args, **kwargs)

    def _get(self, key, *args, **kwargs):
        default = kwargs.pop("default", None)
        result = self.client.get(str(key), *args, **kwargs)
        if result is None:
            return default
        return pickle.loads(result)

    @contextmanager
    def atomic(self):
        wait_for(
            cache.add,
            ["redis-atomic", 'true', self.LOCK_EXPIRE],
            delay=0.3, num_sec=2 * self.LOCK_EXPIRE)
        try:
            yield self
        finally:
            cache.delete("redis-atomic")

    def set(self, key, value, *args, **kwargs):
        with self.atomic():
            return self._set(key, value, *args, **kwargs)

    def get(self, key, *args, **kwargs):
        with self.atomic():
            return self._get(key, *args, **kwargs)

    def delete(self, key, *args, **kwargs):
        with self.atomic():
            return self.client.delete(key, *args, **kwargs)

    @contextmanager
    def appliances_ignored_when_renaming(self, *appliances):
        with self.atomic() as client:
            ignored_appliances = client._get("renaming_appliances")
            if ignored_appliances is None:
                ignored_appliances = set([])
            for appliance in appliances:
                ignored_appliances.add(appliance)
            client._set("renaming_appliances", ignored_appliances)
        yield
        with self.atomic() as client:
            ignored_appliances = client._get("renaming_appliances")
            if ignored_appliances is None:
                ignored_appliances = set([])
            for appliance in appliances:
                try:
                    ignored_appliances.remove(appliance)
                except KeyError:
                    # Something worng happened, ignore
                    pass
            client._set("renaming_appliances", ignored_appliances)

    @property
    def renaming_appliances(self):
        return self.get("renaming_appliances") or set([])


redis = RedisWrapper(redis_client)
sprout_path = project_path.join("sprout")
