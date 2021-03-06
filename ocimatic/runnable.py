import contextlib
import shutil
import subprocess
import time as pytime

from ocimatic.filesystem import FilePath

SIGNALS = {
    1: 'SIGHUP',
    2: 'SIGINT',
    3: 'SIGQUIT',
    4: 'SIGILL',
    5: 'SIGTRAP',
    6: 'SIGABRT',
    7: 'SIGEMT',
    8: 'SIGFPE',
    9: 'SIGKILL',
    10: 'SIGBUS',
    11: 'SIGSEGV',
    12: 'SIGSYS',
    13: 'SIGPIPE',
    14: 'SIGALRM',
    15: 'SIGTERM',
    16: 'SIGURG',
    17: 'SIGSTOP',
    18: 'SIGTSTP',
    19: 'SIGCONT',
    20: 'SIGCHLD',
    21: 'SIGTTIN',
    22: 'SIGTTOU',
    23: 'SIGIO',
    24: 'SIGXCPU',
    25: 'SIGXFSZ',
    26: 'SIGVTALRM',
    27: 'SIGPROF',
    28: 'SIGWINCH',
    29: 'SIGINFO',
    30: 'SIGUSR1',
    31: 'SIGUSR2',
}


class Runnable:
    """An entity that may be executed redirecting stdin and stdout to specific
    files.
    """

    @staticmethod
    def is_callable(file_path):
        return shutil.which(str(file_path)) is not None

    def __init__(self, command, args=None):
        """
        Args:
            bin_path (FilePath|string): Command to execute.
            args (List[string]): List of arguments to pass to the command.
        """
        args = args or []
        command = str(command)
        assert shutil.which(command)
        self._cmd = [command] + args

    def __str__(self):
        return self._cmd[0]

    def run(self, in_path, out_path, args=None, timeout=None):  # pylint: disable=too-many-locals
        """Run binary redirecting standard input and output.

        Args:
            in_path (Optional[FilePath]): Path to redirect stdin from. If None
                input is redirected from /dev/null.
            out_path (Optional[FilePath]): File to redirec stdout to. If None
                output is redirected to /dev/null.
            args (List[str]): Additional parameters

        Returns:
            (bool, str, float): Returns a tuple (status, time, errmsg).
                status is True if the execution terminates with exit code zero
                or False otherwise.
                time corresponds to execution time.
                if status is False errmsg contains an explanatory error
                message, otherwise it contains a success message.
        """
        args = args or []
        assert in_path is None or in_path.exists()
        with contextlib.ExitStack() as stack:
            if in_path is None:
                in_path = FilePath('/dev/null')
            in_file = stack.enter_context(in_path.open('r'))
            if not out_path:
                out_path = FilePath('/dev/null')
            out_file = stack.enter_context(out_path.open('w'))

            start = pytime.monotonic()
            self._cmd.extend(args)
            try:
                complete = subprocess.run(
                    self._cmd,
                    timeout=timeout,
                    stdin=in_file,
                    stdout=out_file,
                    universal_newlines=True,
                    stderr=subprocess.PIPE)
            except subprocess.TimeoutExpired:
                return (False, pytime.monotonic() - start, 'Execution timed out')
            time = pytime.monotonic() - start
            ret = complete.returncode
            status = ret == 0
            msg = 'OK'
            if not status:
                stderr = complete.stderr.strip('\n')
                if stderr and len(stderr) < 100:
                    msg = stderr
                else:
                    if ret < 0:
                        sig = -ret
                        msg = 'Execution killed with signal %d' % sig
                        if sig in SIGNALS:
                            msg += ': %s' % SIGNALS[sig]
                    else:
                        msg = 'Execution ended with error (return code %d)' % ret
            return (status, time, msg)
