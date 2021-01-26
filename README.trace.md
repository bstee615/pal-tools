# `trace`: Python wrapper to generate a dynamic trace of a program execution

This tool is a wrapper around `trace-pintool`, a tool using Intel Pin framework to generate a dynamic trace of a program's execution.
This wrapper supplements `trace-pintool` with information which is only available statically, such as variable declarations without assignments and case statements.

# Run

Trace a command with `trace -- <command>`. See `trace -h` for info.

# Example Usage

This example invokes `trace` to trace execution of an example program `data/test`.

```
[me@centos8 pal-tools]$ gcc -g -O0 data/test.c -odata/test
[me@centos8 pal-tools]$ ./trace -- data/test
/home/me/work/pal-tools/data/test.c:7
/home/me/work/pal-tools/data/test.c:4
/home/me/work/pal-tools/data/test.c:5
/home/me/work/pal-tools/data/test.c:8
/home/me/work/pal-tools/data/test.c:2
/home/me/work/pal-tools/data/test.c:9
/home/me/work/pal-tools/data/test.c:3
/home/me/work/pal-tools/data/test.c:14
/home/me/work/pal-tools/data/test.c:6
/home/me/work/pal-tools/data/test.c:13
```

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
