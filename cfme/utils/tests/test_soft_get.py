import pytest

from cfme.utils.soft_get import MultipleResultsException
from cfme.utils.soft_get import soft_get


def test_soft_get():

    class TestObj:
        a = 1
        b = 2
        c = 3
        aa = 11
        bb = 22
        bbb = 222
        container_image = 'container_image'
        image_registry = 'image_registry'

    test_dict = {'a': 1, 'b': 2, 'c': 3, 'aa': 11, 'bb': 22,
                 'container_image': 'container_image',
                 'image_registry': 'image_registry'}
    for tested in (TestObj, test_dict):
        is_dict = (type(tested) is dict)
        with pytest.raises(AttributeError):
            soft_get(tested, 'no_such_attr', dict_=is_dict)
        with pytest.raises(MultipleResultsException):
            soft_get(tested, 'a', dict_=is_dict, best_match=False)
        with pytest.raises(AttributeError):
            soft_get(tested, 'Aa', dict_=is_dict, case_sensitive=True)
        if not is_dict:
            with pytest.raises(TypeError):
                soft_get(tested, 'a', dict_=True)

        assert soft_get(tested, 'a', dict_=is_dict) == 1
        assert soft_get(tested, 'bb', dict_=is_dict) == 22
        assert soft_get(tested, 'image', dict_=is_dict) == 'image_registry'
        assert soft_get(tested, 'image', dict_=is_dict, dont_include=['registry']) \
            == 'container_image'
