from pathlib import Path
from mylog import log
import subprocess
from .location import Location


def parse_pinlog(logfile):
    """
    Parse a Pin log file and return the trace locations.
    """
    logtext = logfile.read_text()
    loglines = logtext.splitlines()
    locations = []
    for line in loglines:
        split = line.split(':')
        filepath = split[0]
        lineno = int(split[1])
        column = int(split[2])
        locations.append(Location(filepath, lineno, column))
    return locations


class Pin:
    def __init__(self, args):
        self.root = args.pin_root
        self.exe = self.root / 'pin'
        self.lib = self.root / 'source/tools/trace-pintool/obj-intel64/trace.so'
        self.keep_logfile = args.keep_logfile

    def is_valid(self):
        """
        Heuristic checks to make sure the necessary files are there.
        """
        return all((self.root.is_dir(), self.exe.is_file(), self.lib.is_file()))

    @classmethod
    def do_wizard(_, args, install_sh):
        """
        Get Pin installation from root.
        If Pin is not at the expected location, do the interactive wizard with install_sh.
        """
        root = args.pin_root
        pin = Pin(args)
        if not pin.is_valid():
            log.warn(f'{root} is not a valid Pin installation.')
            if not install_sh.is_file():
                log.error(f'Could not execute {install_sh}.')
                exit(1)
            else:
                log.warn(
                    f'See {install_sh} for the recommended method for installing Pin.')
                yn = input(
                    f'Should I install it at {root}? [type y to install, anything else to quit]: ')
                if yn == 'y':
                    cmd = f'bash {install_sh.absolute()} {root.name}'
                    log.debug(
                        f'Running Bash script install.sh with "{cmd}" in directory "{root}"')
                    proc = subprocess.Popen(
                        cmd.split(), cwd=root.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    stdout, _ = proc.communicate()
                    for l in stdout.decode().splitlines():
                        log.info(f'**[{install_sh.name}]** {l}')
                    if proc.returncode == 0:
                        log.info(f'Ran {install_sh} successfully.')
                    else:
                        log.error(f'Could not execute {install_sh}.')
                        exit(1)
                else:
                    exit(1)

        pin = Pin(args)
        if not pin.is_valid():
            log.error(f'Something is wrong with the Pin environment at {root}')

        return pin

    def run(self, target, target_args):
        """
        Run Pin. Collect results in temporary file pin.log
        and return a list of trace locations (filepath:lineno:column).
        """
        if not target.is_file():
            log.error(f'No such file for target executable: {target}')
            return []

        if not self.exe.is_file():
            log.error(f'No such file for Pin executable: {self.exe}')
            return []
        if not self.lib.is_file():
            log.error(f'No such file for trace-pintool: {self.lib}')
            return []

        logfile = Path('pin.log')
        errorfile = Path('error.log')
        try:
            # Clear files if present from old executions
            if logfile.is_file():
                logfile.unlink()
            if errorfile.is_file():
                errorfile.unlink()

            # Run Pin
            cmd = f'{self.exe} -error_file {errorfile.absolute()} -t {self.lib} -o {logfile} -c -- {target.absolute()}'
            log.debug(f'pin command: {cmd}')
            args = cmd.split() + target_args
            p = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            stdout, _ = p.communicate()
            return_code = p.returncode
            args_str = ' '.join(args)

            # Pin tool exits 1 on success ¯\_(ツ)_/¯ use errorfile to detect errors
            log.info(
                f'Got return code {return_code} running pin with command: "{args_str}"')
            if errorfile.is_file():
                log.warn(f'Echoing Pin output stream:')
                for l in stdout.decode().splitlines():
                    log.warn(f'* {l}')
                errorfile.unlink()
                raise Exception(
                    f'Pin had an error while running. See {errorfile} for more information.')
            if errorfile.is_file():
                errorfile.unlink()

            if not logfile.is_file():
                raise Exception(
                    f'Something went wrong running Pin -- {logfile} is missing.')
            return parse_pinlog(logfile)
        finally:
            if logfile.is_file() and not self.keep_logfile:
                logfile.unlink()
