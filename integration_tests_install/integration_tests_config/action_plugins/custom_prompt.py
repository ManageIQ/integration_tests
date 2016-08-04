# Not extensively tested
# This is modification of:
# https://gist.githubusercontent.com/confiks/6d7b0ee3e137df01b758/raw/6b31d61151c4199e5121c34c841f7168850a6071/ask_key.py
# Put this script in the action_plugins directory of your playbook directory
# If you have issues, please report it in the comments (or fork and fix)

# Usage:
# - name: "Ask the user if we should continue. Accept only y, n, r chars."
#   action: >
#       custom_prompt prompt="Continue? Yes / No / Random (y/n/r)?" accepted_keys="['y', 'n' 'r' ]"
#   register: answer

# - name: "Ask the user for any strings."
#   action: custom_prompt prompt="What is your name?"
#   register: answer
#
# The pressed key is now in answer.key

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import termios
import tty
from os import isatty

from ansible.plugins.action import ActionBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class ActionModule(ActionBase):
    ''' Ask the user to input a key '''

    VALID_ARGS = set(["prompt", "accepted_keys"])
    REQUIRED_ARGS = set(["prompt"])

    BYPASS_HOST_LOOP = True

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        for arg in self._task.args:
            if arg not in self.VALID_ARGS:
                return {"failed": True, "msg": "{} is not a valid option in ask".format(arg)}

        for arg in self.REQUIRED_ARGS:
            if arg not in self._task.args:
                return {"failed": True, "msg": "{} is required in ask".format(arg)}

        result = super(ActionModule, self).run(tmp, task_vars)

        fd = None
        old_settings = None

        try:
            fd = self._connection._new_stdin.fileno()
        except ValueError:
            pass

        if fd is not None:
            if isatty(fd):
                old_settings = termios.tcgetattr(fd)
                # tty.setraw(fd)
                tty.setcbreak(fd)

                termios.tcflush(self._connection._new_stdin, termios.TCIFLUSH)

                new = termios.tcgetattr(fd)
                new[3] = new[3] | (termios.ECHO | termios.ECHONL | termios.ICANON)
                termios.tcsetattr(fd, termios.TCSADRAIN, new)
        else:
            return {"failed": True,
                "msg": "For some reason, we couldn't access the connection tty."}

        display.display(self._task.args["prompt"] + "\r")

        if "accepted_keys" in self._task.args:
            while True:
                key = self._connection._new_stdin.read(1)
                if key == '\x03':
                    result["failed"] = True
                    result["msg"] = "User requested to cancel."
                    break
                elif key in self._task.args["accepted_keys"]:
                    result["key"] = key
                    break
        elif "accepted_keys "not in self._task.args:
            key = self._connection._new_stdin.readline().strip('\n')
            if key == '\x03':
                result["failed"] = True
                result["msg"] = "User requested to cancel."
            elif key == '\n':
                result["key"] = ""
            else:
                result["key"] = key

        if old_settings is not None and isatty(fd):
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return result
