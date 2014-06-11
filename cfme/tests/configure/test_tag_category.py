from cfme.configure.configuration import Category
from utils.update import update
from utils.randomness import generate_lowercase_random_string, generate_random_string


def test_category_crud():
    cg = Category(name=generate_lowercase_random_string(size=8),
                  description=generate_random_string(size=32),
                  display_name=generate_random_string(size=32))
    cg.create()
    with update(cg):
        cg.description = generate_random_string(size=32)
    cg.delete(cancel=False)
