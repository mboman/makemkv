"""pytest fixtures."""

import contextlib
import fnmatch
import os
import pty
import subprocess
import time

import py
import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, '..'))


def run(command=None, args=None, output=None, image_id=None, environ=None, cwd=None):
    """Run a command and return the output. Supports string and py.path paths.

    :raise CalledProcessError: Command exits non-zero.

    :param iter command: Command to run.
    :param iter args: List of command line arguments to insert to command.
    :param str output: Path to bind mount to /output when `command` is None.
    :param str image_id: Docker image to use instead of mboman/makemkv.
    :param dict environ: Environment variables to set/override in the command.
    :param str cwd: Current working directory. Default is tests directory.

    :return: Command stdout and stderr output.
    :rtype: tuple
    """
    if command is None:
        command = ['docker', 'run', '--device=/dev/cdrom', '-e', 'DEBUG=true', image_id or 'mboman/makemkv']
        if output:
            command = command[:-1] + ['-v', '{}:/output'.format(output)] + command[-1:]
    if args:
        command = command[:-1] + list(args) + command[-1:]

    env = os.environ.copy()
    if environ:
        env.update(environ)

    # Simulate stdin pty so 'docker run -it' doesn't complain.
    if command[0] in ('bash', 'docker'):
        master, slave = pty.openpty()
    else:
        master, slave = 0, 0

    # Determine timeout.
    if command[0] in ('docker',):
        timeout = 120
    else:
        timeout = 30

    # Run command.
    try:
        result = subprocess.run(
            [str(i) for i in command], check=True, cwd=cwd or HERE, env=env,
            stderr=subprocess.PIPE, stdin=slave or None, stdout=subprocess.PIPE,
            timeout=timeout
        )
    finally:
        if slave:
            os.close(slave)
        if master:
            os.close(master)

    return result.stdout, result.stderr


def cdstatus():
    """Return the file path to the loaded ISO or None if nothing is loaded.

    :return: Path to loaded ISO.
    :rtype: str
    """
    stdout = run(['cdemu', 'status'])[0]
    for columns in (l.split() for l in stdout.splitlines()):
        if columns[:2] == [b'0', b'True']:
            return columns[2].decode('utf8')
    return None


def cdload(path=None):
    """Load the ISO into the virtual CD-ROM device.

    :param path: File path of ISO file to load if not sample.iso.
    """
    path = path or 'sample.iso'

    try:
        run(['cdemu', 'load', '0', path])
    except subprocess.CalledProcessError as exc:
        if b'AlreadyLoaded' not in exc.stderr:
            raise
        loaded = cdstatus()
        if not loaded or os.path.realpath(loaded) != os.path.realpath(path):
            cdunload()
            return cdload(path)

    for _ in range(50):
        if os.path.exists('/dev/cdrom'):
            return
        time.sleep(0.1)
    if not os.path.exists('/dev/cdrom'):
        raise IOError('Failed to load cdemu device!')


def cdunload():
    """Eject the ISO from the virtual CD-ROM device."""
    for _ in range(3):
        run(['cdemu', 'unload', '0'])
        for _ in range(50):
            if not os.path.exists('/dev/cdrom'):
                return
            time.sleep(0.1)
    if os.path.exists('/dev/cdrom'):
        raise IOError('Failed to unload cdemu device!')


@contextlib.contextmanager
def container_ids_diff():
    """Find the ID of the container(s) created by "docker run" commands."""
    diff = list()
    command = ['docker', 'ps', '-aqf', 'ancestor=mboman/makemkv']
    old_cids = set(run(command)[0].splitlines())

    # Yield to let caller execute "docker run".
    yield diff

    # In case caller doesn't block wait up to 10 seconds for at least one new container to appear.
    for _ in range(100):
        container_ids = set(run(command)[0].splitlines())
        diff.extend(i.decode('utf8') for i in container_ids - old_cids)
        if diff:
            break
        time.sleep(0.1)


def verify(output, gid=None, uid=None, modes=None):
    """Verify the output directory using sudo.

    :param py.path.local output: Root output directory.
    :param int gid: Verify owner group ID of files.
    :param int uid: Verify owner user ID of files.
    :param iter modes: Verify mode of (directory, file).
    """
    stdout, stderr = run(['sudo', 'find', output, '-mindepth', '1', '-printf', r'%M %U %G %s %P\n'])
    assert not stderr

    tree = list()
    for cols in (l.split(b' ', 4) for l in stdout.splitlines()):
        tree.append(dict(
            mode=cols[0].decode('utf8'),
            uid=int(cols[1]),
            gid=int(cols[2]),
            size=int(cols[3]),
            relpath=cols[4],
        ))

    # Verify directory tree.
    assert len(tree) == 2
    assert fnmatch.fnmatch(tree[0]['relpath'], b'Sample_2017-04-15-15-16-14-00_???')
    assert fnmatch.fnmatch(tree[1]['relpath'], b'Sample_2017-04-15-15-16-14-00_???/title00.mkv')

    # Verify subdirectory.
    if gid is not None:
        assert tree[0]['gid'] == gid
    if uid is not None:
        assert tree[0]['uid'] == uid
    if modes is not None:
        assert tree[0]['mode'] == modes[0]

    # Verify MKV file.
    assert 17345210 < tree[1]['size'] < 17345220  # Target size is 17345216. May deviate a byte or two.
    if gid is not None:
        assert tree[1]['gid'] == gid
    if uid is not None:
        assert tree[1]['uid'] == uid
    if modes is not None:
        assert tree[1]['mode'] == modes[1]


def verify_failed_file(output):
    """Verify presence of "failed" file.

    :param py.path.local output: Root output directory.
    """
    stdout, stderr = run(['sudo', 'find', output, '-name', 'failed', '-printf', r'%P\n'])
    assert not stderr

    tree = stdout.splitlines()
    assert len(tree) == 1
    assert fnmatch.fnmatch(tree[0], b'Sample_2017-04-15-15-16-14-00_???/failed')


def pytest_namespace():
    """Add objects to the pytest namespace. Can be retrieved by importing pytest and accessing pytest.<name>.

    :return: Namespace dict.
    :rtype: dict
    """
    return dict(
        cdload=cdload,
        cdunload=cdunload,
        container_ids_diff=container_ids_diff,
        ROOT=py.path.local(ROOT),
        run=run,
        verify=verify,
        verify_failed_file=verify_failed_file,
    )


@pytest.fixture
def cdemu():
    """Load sample.iso before running test function."""
    cdload()


@pytest.fixture(scope='session', name='tmpdir_session')
def _tmpdir_session(request, tmpdir_factory):
    """A tmpdir fixture for the session scope. Persists throughout the pytest session."""
    return tmpdir_factory.mktemp(request.session.name)


@pytest.fixture
def cdemu_truncated(tmpdir_session):
    """Load truncated.iso before running test function.

    :param py.path.local tmpdir_session: conftest fixture.
    """
    path = tmpdir_session.join('truncated.iso')
    if not path.check():
        py.path.local('sample.iso').copy(path)
        with path.open('rb+') as handle:
            handle.truncate(1024000)
    cdload(path)
