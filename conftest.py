import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: live API call — run with: pytest -m integration",
    )
