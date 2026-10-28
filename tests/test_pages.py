"""Public-source staging must not copy ignored files or follow outside links."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

try:
    from scripts.stage_pages import stage
except ModuleNotFoundError:
    stage = None  # Runtime-only test mounts intentionally omit website tools.


@unittest.skipIf(stage is None, 'Pages source tools are not included in runtime-only tests')
class PagesStagingTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name).resolve()
        (self.root / '.gitignore').write_text('.ai/\nAGENTS.md\n', encoding='utf-8')

    def initialize_git(self):
        if not shutil.which('git'):
            self.skipTest('Public-source staging requires a host Git checkout')
        subprocess.run(['git', 'init', '--quiet', str(self.root)], check=True)

    def build(self):
        with redirect_stdout(io.StringIO()):
            return stage(self.root)

    def test_unstaged_public_edits_are_copied_without_ignored_files(self):
        self.initialize_git()
        readme = self.root / 'README.md'
        readme.write_text('Old overview', encoding='utf-8')
        subprocess.run(['git', 'add', 'README.md'], cwd=self.root, check=True)
        readme.write_text('Current overview', encoding='utf-8')
        (self.root / 'AGENTS.md').write_text('Private', encoding='utf-8')
        memory = self.root / '.ai' / 'memory.txt'
        memory.parent.mkdir()
        memory.write_text('Private', encoding='utf-8')
        destination = self.build()
        self.assertEqual((destination / 'README.md').read_text(), 'Current overview')
        self.assertFalse((destination / 'AGENTS.md').exists())
        self.assertFalse((destination / '.ai').exists())

    def test_accidentally_tracked_private_file_preserves_previous_stage(self):
        self.initialize_git()
        (self.root / 'README.md').write_text('Overview', encoding='utf-8')
        destination = self.build()
        (self.root / 'AGENTS.md').write_text('Private', encoding='utf-8')
        subprocess.run(['git', 'add', '--force', 'AGENTS.md'], cwd=self.root, check=True)
        with self.assertRaisesRegex(ValueError, 'Private files'):
            self.build()
        self.assertEqual((destination / 'README.md').read_text(), 'Overview')

    @patch('scripts.stage_pages.subprocess.check_output', return_value=b'README.md\0')
    def test_external_symlink_is_rejected_before_clearing_previous_stage(self, listing):
        (self.root / 'README.md').write_text('Overview', encoding='utf-8')
        destination = self.build()
        with tempfile.TemporaryDirectory() as outside:
            secret = Path(outside) / 'secret.txt'
            secret.write_text('Private', encoding='utf-8')
            link = self.root / 'linked.txt'
            try:
                link.symlink_to(secret)
            except OSError:
                self.skipTest('Creating symlinks is unavailable on this host')
            try:
                listing.return_value = b'README.md\0linked.txt\0'
                with self.assertRaisesRegex(ValueError, 'ordinary files'):
                    self.build()
                self.assertEqual((destination / 'README.md').read_text(), 'Overview')
            finally:
                link.unlink()


if __name__ == '__main__':
    unittest.main()
