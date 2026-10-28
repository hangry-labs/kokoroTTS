"""Guard targeted security pins without upgrading the model-facing stack."""

from pathlib import Path
import tomllib
import unittest


class DependencySecurityTests(unittest.TestCase):
    def test_security_pins_agree_in_inputs_extra_and_both_locks(self):
        root = Path(__file__).resolve().parents[1]
        project = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))
        lock = tomllib.loads((root / 'uv.lock').read_text(encoding='utf-8'))
        versions = {package['name']: package['version'] for package in lock['package']}
        for name, version in (
            ('certifi', '2026.10.18'),
            ('filelock', '4.2.1'),
            ('opentelemetry-api', '1.45.1'),
        ):
            with self.subTest(package=name):
                pin = f'{name}=={version}'
                for filename in ('requirements.in', 'requirements.txt'):
                    self.assertIn(pin, (root / filename).read_text(encoding='utf-8').splitlines())
                self.assertIn(pin, project['project']['optional-dependencies']['server'])
                self.assertEqual(versions[name], version)


if __name__ == '__main__':
    unittest.main()
