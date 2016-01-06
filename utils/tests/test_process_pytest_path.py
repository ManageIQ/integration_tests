# -*- coding: utf-8 -*-
import pytest

from utils import process_pytest_path


@pytest.mark.parametrize(("input_string", "expected_result"), [
    ("", []),
    ("a/b/c", ["a", "b", "c"]),
    ("//a////b//////c////", ["a", "b", "c"]),
    ("abc[def]", ["abc[def]"]),
    ("abc[def/ghi]", ["abc[def/ghi]"]),
    ("a/b/c[d/e]/f/g", ["a", "b", "c[d/e]", "f", "g"]),
    ("a/b/c[d/e]/f/g/", ["a", "b", "c[d/e]", "f", "g"])],
    ids=[
        "empty", "simple", "manyslashes", "simpleparam", "paramslash", "path-paramslash",
        "endslash"])
def test_process_pytest_path(input_string, expected_result):
    assert process_pytest_path(input_string) == expected_result
