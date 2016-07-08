# -*- coding: utf-8 -*-
from .objects import Widget


class Input(Widget):
    def __init__(self, id_or_name, by_id=False):
        self.id_or_name = id_or_name
        self.by_id = by_id
