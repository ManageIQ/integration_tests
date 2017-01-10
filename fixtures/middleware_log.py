import pytest
from utils.log_validator import LogValidator


@pytest.yield_fixture(scope='function')
def middleware_evm_log_no_error():
    evm_tail = LogValidator('/var/www/miq/vmdb/log/evm.log',
                            skip_patterns=['.*ERROR.*API.*MIQ(Api::ApiController.api_error).*'],
                            failure_patterns=['.*ERROR.*'])
    evm_tail.fix_before_start()
    yield
    evm_tail.validate_logs()
