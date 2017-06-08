#!/usr/bin/env python2
import argparse
import subprocess
import socket
from wait_for import wait_for

from dockerbot import SeleniumDocker
from utils.net import random_port
from utils.conf import docker as docker_conf


def vnc_ready(addr, port):
    try:
        soc = socket.create_connection((addr, port), timeout=2)
    except socket.error:
        return False
    # docker-proxy opens the port immediately after container is started.
    # Receive data from the socket to check if VNC session is really running.
    if not soc.recv(1024):
        return False
    soc.close()
    return True


def main():
    """Main function for running"""
    parser = argparse.ArgumentParser(argument_default=None)

    interaction = parser.add_argument_group('Ports')
    interaction.add_argument('--watch', help='Opens VNC session',
                             action='store_true', default=False)
    interaction.add_argument('--vnc', help='Chooses VNC port',
                             default=random_port())
    interaction.add_argument('--webdriver', help='Chooses WebDriver port',
                             default=random_port())
    interaction.add_argument('--image', help='Chooses WebDriver port',
                             default=docker_conf.get('selff', 'cfme/sel_ff_chrome'))
    interaction.add_argument('--vncviewer', help='Chooses VNC viewer command',
                             default=docker_conf.get('vncviewer'))

    args = parser.parse_args()
    ip = '127.0.0.1'

    print("Starting container...")

    dkb = SeleniumDocker(bindings={'VNC_PORT': (5999, args.vnc),
                                   'WEBDRIVER': (4444, args.webdriver)},
                         image=args.image)
    dkb.run()

    if args.watch:
        print
        print("  Waiting for VNC port to open...")
        wait_for(lambda: vnc_ready(ip, args.vnc), num_sec=60, delay=2)

        print("  Initiating VNC watching...")
        if args.vncviewer:
            viewer = args.vncviewer
            if '%I' in viewer or '%P' in viewer:
                viewer = viewer.replace('%I', ip).replace('%P', str(args.vnc))
                ipport = None
            else:
                ipport = '{}:{}'.format(ip, args.vnc)
            cmd = viewer.split()
            if ipport:
                cmd.append(ipport)
        else:
            cmd = ['xdg-open', 'vnc://{}:{}'.format(ip, args.vnc)]
        subprocess.Popen(cmd)

    print(" Hit Ctrl+C to end container")
    try:
        dkb.wait()
    except KeyboardInterrupt:
        print(" Killing Container.....please wait...")
    dkb.kill()
    dkb.remove()


if __name__ == "__main__":
    main()
