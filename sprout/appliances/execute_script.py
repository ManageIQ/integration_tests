# -*- coding: utf-8 -*-
import inspect


def execute_script(script):
    """Executes script with models and tasks in the environment."""
    from appliances import models, tasks
    from celery.local import Proxy
    env = {}
    for var in dir(models):
        o = getattr(models, var)
        if (inspect.isclass(o) and issubclass(o, models.MetadataMixin) and
                o is not models.MetadataMixin):
            env[var] = o
    for var in dir(tasks):
        o = getattr(tasks, var)
        if isinstance(o, Proxy) and type(o) is not Proxy:
            env[var] = o
    try:
        exec script in env
    except Exception as e:
        return e
    else:
        return None
