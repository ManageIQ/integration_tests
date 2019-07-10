import sys

from . import IN_VIRTUAL_ENV
from . import main
from . import mk_parser
IS_SCRIPT = sys.argv[0] == __file__

if IS_SCRIPT:
    if IN_VIRTUAL_ENV:
        parser = mk_parser(sys.prefix)
    else:
        parser = mk_parser('.cfme_venv')
    main(parser.parse_args())
