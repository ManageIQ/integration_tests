#!/usr/bin/env python3
import datetime
import sys

from cfme.utils.conf import env


def main():
    print(datetime.date.today())
    if env.appliances[0].hostname == "SPROUT_SHOULD_OVERRIDE_THIS":
        print("sprout provisioning failed")
        sys.exit(1)
    else:
        print("sprout provisioning worked")


if __name__ == '__main__':
    main()
