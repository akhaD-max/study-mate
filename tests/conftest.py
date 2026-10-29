import os

import django
import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "applications.demo_settings")
django.setup()


@pytest.fixture(scope="session", autouse=True)
def django_test_environment():
    from django.test.utils import (
        setup_databases,
        setup_test_environment,
        teardown_databases,
        teardown_test_environment,
    )

    setup_test_environment()
    config = setup_databases(verbosity=1, interactive=False)
    try:
        yield
    finally:
        teardown_databases(config, verbosity=1)
        teardown_test_environment()
