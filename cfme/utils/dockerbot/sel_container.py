#!/usr/bin/env python3
import socket
import subprocess
import sys

import click
from wait_for import TimedOutError
from wait_for import wait_for

from cfme.utils.conf import docker as docker_conf
from cfme.utils.dockerbot.dockerbot import SeleniumDocker
from cfme.utils.net import random_port


def vnc_ready(addr, port):
    """Checks if VNC port is open and ready"""
    try:
        soc = socket.create_connection((addr, int(port)), timeout=2)
    except socket.error:
        return False
    # docker-proxy opens the port immediately after container is started.
    # Receive data from the socket to check if VNC session is really running.
    if not soc.recv(1024):
        return False
    soc.close()
    return True


@click.command(help='Starts selenium container for testing against')
@click.option('--watch', help='Opens VNC session', default=False, is_flag=True)
@click.option('--vnc', help='Chooses VNC port', default=5900)
@click.option('--webdriver', help='Chooses webdriver port', default=4444)
@click.option('--image', help='Chooses selenium container image',
              default=docker_conf.get('selff', 'cfmeqe/sel_ff_chrome'))
@click.option('--vncviewer', help='Chooses VNC viewer command',
              default=docker_conf.get('vncviewer', 'vinagre'))
@click.option('--random-ports', is_flag=True, default=False,
              help='Choose random ports for VNC, webdriver, (overrides --webdriver and --vnc)')
def main(watch, vnc, webdriver, image, vncviewer, random_ports):
    """Main function for running"""

    ip = '127.0.0.1'

    print("Starting container...")
    vnc = random_port() if random_ports else vnc
    webdriver = random_port() if random_ports else webdriver

    dkb = SeleniumDocker(bindings={'VNC_PORT': (5999, vnc),
                                   'WEBDRIVER': (4444, webdriver)},
                         image=image)
    dkb.run()

    if watch:
        print("")
        print("  Waiting for VNC port to open...")
        try:
            wait_for(lambda: vnc_ready(ip, vnc), num_sec=60, delay=2, message="Wait for VNC Port")
        except TimedOutError:
            print("   Could not wait for VNC port, terminating...")
            dkb.kill()
            dkb.remove()
            sys.exit(127)

        print("  Initiating VNC watching...")
        if vncviewer:
            viewer = vncviewer
            if '%I' in viewer or '%P' in viewer:
                viewer = viewer.replace('%I', ip).replace('%P', str(vnc))
                ipport = None
            else:
                ipport = '{}:{}'.format(ip, vnc)
            cmd = viewer.split()
            if ipport:
                cmd.append(ipport)
        else:
            cmd = ['xdg-open', 'vnc://{}:{}'.format(ip, vnc)]
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
