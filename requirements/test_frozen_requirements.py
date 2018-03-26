import pathlib2

HERE = pathlib2.Path(__file__).resolve().parent
FROZEN = HERE.joinpath('frozen.txt')
FROZEN_DOC = HERE.joinpath('frozen_docs.txt')


def test_match_files():
    with FROZEN.open() as fp:
        frozen = dict(x.strip().split('==') for x in fp)
    with FROZEN_DOC.open() as fp:
        frozen_doc = dict(x.strip().split('==') for x in fp)

    expected_frozen_doc = {k: v for k, v in frozen.items() if k in frozen_doc}
    assert expected_frozen_doc == frozen_doc
