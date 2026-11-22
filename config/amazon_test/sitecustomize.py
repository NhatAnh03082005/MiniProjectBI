"""Process-local guard for manually launched TEST Mage/dbt commands."""
import os
if os.environ.get('AMAZON_TEST_CONNECTIONS') == '1':
    try:
        from etl_monitoring.connection import install_process_guard
        install_process_guard()
    except BaseException:
        # Python normally tolerates sitecustomize failures. TEST must fail closed.
        os._exit(78)
