import warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore', ImportWarning)
    __import__('oslo_i18n')
