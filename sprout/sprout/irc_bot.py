# -*- coding: utf-8 -*-
from sprout import settings

import json
import pika

REQUIRED = {'PIKA_USER', 'PIKA_PASS', 'PIKA_HOST', 'PIKA_CHANNEL', 'PIKA_ROUTING_KEY'}


def send_message(message):
    if not any(hasattr(settings, item) for item in REQUIRED):
        return

    url = "amqp://" + settings.PIKA_USER + ":" + settings.PIKA_PASS + "@" + settings.PIKA_HOST
    params = pika.URLParameters(url)
    params.socket_timeout = 5

    try:
        connection = pika.BlockingConnection(params)  # Connect to CloudAMQP
        channel = connection.channel()

        message = json.dumps({'channel': settings.PIKA_CHANNEL, 'body': message})

        channel.basic_publish(exchange='',
                              routing_key=settings.PIKA_ROUTING_KEY,
                              body=message)
        connection.close()
    except:
        # Don't bother if we cannot connect
        pass
