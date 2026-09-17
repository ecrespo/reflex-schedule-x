"""Run tests from a scratch directory: rx.asset(shared=True) links files into ./assets/external."""

import os
import tempfile


def pytest_sessionstart(session):
    # Change directory only after pytest has resolved `testpaths`, but before test modules are imported.
    os.chdir(tempfile.mkdtemp(prefix="reflex-schedule-x-tests-"))
