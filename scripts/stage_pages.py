"""Stage public Git files for a local Pages build, including unstaged edits.

Git ignore rules and explicit private-file checks apply before Jekyll reads the
tree. Output is always confined to this project's ignored preview directory.
"""
from pathlib import Path, PurePosixPath
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def private_path(name):
    parts = PurePosixPath(name).parts
    private_names = {'.ai', '.idea', 'todo', 'AGENTS.md', 'UPSTREAM_ISSUES.md', 'UPSTREAM_PULL_REQUESTS.md'}
    return any(part in private_names for part in parts) or any(
        parts[index:index + 2] == ('docs', 'internal') for index in range(len(parts) - 1))


def stage(root=ROOT):
    root = root.resolve()
    preview = root / '.ai/scratch/pages'
    destination = (preview / 'source').resolve()
    if not destination.is_relative_to(preview.resolve()) or destination == preview.resolve():
        raise ValueError('The Pages source stage must stay inside its preview directory.')
    names = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=root).decode('utf-8').split('\0')
    names = sorted(set(filter(None, names)))
    if any(private_path(name) for name in names):
        raise ValueError('Private files must be untracked and ignored before building Pages.')
    # Resolve/verify all candidates before clearing our previous staged output.
    files = []
    for name in names:
        source = root / name
        if not source.exists():
            continue
        if source.is_symlink() or not source.resolve().is_relative_to(root):
            raise ValueError('Pages inputs must be ordinary files inside the checkout.')
        if source.is_file():
            files.append((source, destination / name))
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for source, target in files:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print(f'Staged {len(files)} public files for Pages.')
    return destination


if __name__ == '__main__':
    stage()
