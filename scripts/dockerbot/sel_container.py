#!/usr/bin/env python2
import argparse

from dockerbot import SeleniumDocker
from utils.net import random_port
from utils.conf import docker as docker_conf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(argument_default=None)

    interaction = parser.add_argument_group('Ports')
    interaction.add_argument('--vnc', help='Chooses VNC port',
                             default=random_port())
    interaction.add_argument('--webdriver', help='Choose WebDriver port',
                             default=random_port())
    interaction.add_argument('--image', help='Choose WebDriver port',
                             default=docker_conf.get('selff', 'cfme/sel_ff_chrome'))

    args = parser.parse_args()

    print "Starting container..."

    dkb = SeleniumDocker(bindings={'VNC_PORT': (5999, args.vnc),
                                   'WEBDRIVER': (4444, args.webdriver)},
                         image=args.image)
    dkb.run()
    print " Hit Ctrl+C to end container"
    try:
        dkb.wait()
    except KeyboardInterrupt:
        print " Killing Container.....please wait..."
        pass
    dkb.kill()
    dkb.remove()
