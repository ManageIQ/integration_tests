# -*- coding: utf-8 -*-
from utils import InstanceClassMethod


class ClassWithCompleteDefinition(object):
    @InstanceClassMethod
    def execute(self, x):
        return (self, x)

    @execute.classmethod
    def execute(cls):
        return cls


class ClassWithIncompleteDefinition(object):
    @InstanceClassMethod
    def execute(self, x):
        return (self, x)


def test_check_complete_definition():
    inst = ClassWithCompleteDefinition()
    assert inst.execute(1) == (inst, 1)
    assert ClassWithCompleteDefinition.execute() is ClassWithCompleteDefinition


def test_check_partial_definition():
    inst = ClassWithCompleteDefinition()
    assert inst.execute(1) == (inst, 1)
    assert ClassWithIncompleteDefinition.execute(1) == (ClassWithIncompleteDefinition, 1)
