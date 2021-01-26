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
        split_index = line.rindex(':')
        filepath = line[:split_index]
        lineno = int(line[split_index+1:])
        locations.append(Location(filepath, lineno))
    return locations


class Pin:
    def __init__(self, pin_root):
        self.root = pin_root
        self.exe = self.root / 'pin'
        self.lib = self.root / 'source/tools/trace-pintool/obj-intel64/trace.so'

    def is_valid(self):
        """
        Heuristic checks to make sure the necessary files are there.
        """
        return all((self.root.is_dir(), self.exe.is_file(), self.lib.is_file()))

    @classmethod
    def do_wizard(_, pin_root, install_sh):
        """
        Get Pin installation from root.
        If Pin is not at the expected location, do the interactive wizard with install_sh.
        """
        pin = Pin(pin_root)
        if not pin.is_valid():
            log.warn(f'{pin_root} is not a valid Pin installation.')
            if not install_sh.is_file():
                log.error(f'Could not execute {install_sh}.')
                exit(1)
            else:
                log.warn(f'See {install_sh} for the recommended method for installing Pin.')
                yn = input(f'Should I install it at {pin_root}? [type y to install, anything else to quit]: ')
                if yn == 'y':
                    cmd = f'bash {install_sh.absolute()} {pin_root.name}'
                    log.debug(f'Running Bash script install.sh with "{cmd}" in directory "{pin_root}"')
                    proc = subprocess.Popen(cmd.split(), cwd=pin_root.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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

        pin = Pin(pin_root)
        if not pin.is_valid():
            log.error(f'Something is wrong with the Pin environment at {pin_root}')

        return pin
    
    def run(self, target, target_args):
        """
        Run Pin. Collect results in temporary file pin.log
        and return a list of trace locations (filepath:lineno).
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
        cmd = f'{self.exe} -t {self.lib} -o {logfile} -- {target.absolute()}'
        args = cmd.split() + target_args
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, _ = p.communicate()
        return_code = p.returncode
        args_str = ' '.join(args)
        log.debug(f'Ran "{args_str}" with return code {return_code}')

        # Pin tool exits 1 on success ¯\_(ツ)_/¯
        log.info(f'Got return code {return_code} running pin with command: "{cmd}"')
        log.info(f'Echoing output stream:')
        for l in stdout.decode().splitlines():
            log.info(f'**[{target.name}]** {l}')
        
        if not logfile.is_file():
            log.error(f'Something went wrong logging to {logfile}.')
            return []
        
        return parse_pinlog(logfile)