# -*- coding: utf-8 -*-


class ViaREST(object):

    name = "REST"

    def __init__(self, owner):
        self.owner = owner

    @property
    def appliance(self):
        return self.owner

    def __str__(self):
        return 'REST'
