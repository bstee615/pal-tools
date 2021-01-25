# `trace`: Python wrapper to generate a dynamic trace of a program execution

This tool is a wrapper around `trace-pintool`, a tool using Intel Pin framework to generate a dynamic trace of a program's execution.
This wrapper supplements `trace-pintool` with information which is only available statically, such as variable declarations without assignments and case statements.

# Setup

TL;DR: run `tools/trace/install.sh` in directory `tools/trace` and install libraries listed under **Extra Requirements**.

## Extra Requirements
Some extra requirements are needed.
```
sudo yum install clang-devel ncurses-devel ncurses-compat-libs # Install Clang and libclang dependencies
pip3 install libclang pathlib # Install Python packages
```

## Pin tool
Pin must be installed under `tools/trace`, or an alternative location for a Pin installation can be specified with `-p`.
Pin is distributed [here](http://software.intel.com/sites/landingpage/pintool/downloads/pin-3.16-98275-ge0db48c31-gcc-linux.tar.gz).
`trace-pintool` is distributed [here](https://github.com/bstee615/trace-pintool). It must be unpacked into `<pin-root>/source/tools` and built.
`tools/trace/install.sh` automates this process in the current working directory. Please run in `tools/trace` and before you run, make sure you are set up to build Pin.