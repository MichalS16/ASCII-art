"""Shared test mixin for isolating filesystem side effects."""

import os
import shutil
import tempfile


class IsolatedTempCwdMixin:
    """Runs each test in a fresh temp cwd, since the functions under test
    create results_dir (or similar) as a side effect and shouldn't litter
    the repo root."""

    def setUp(self):
        super().setUp()
        self._cwd = os.getcwd()
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.addCleanup(os.chdir, self._cwd)
        os.chdir(self.tmpdir)
