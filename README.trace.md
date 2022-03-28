# `trace`: Python wrapper to generate a dynamic trace of a program execution

This tool is a wrapper around `trace-pintool`, a tool using Intel Pin framework to generate a dynamic trace of a program's execution.
This wrapper supplements `trace-pintool` with information which is only available statically, such as variable declarations without assignments and case statements.

# Run

Trace a command with `trace -- <command>`. See `trace -h` for info.

# Example Usage

This example invokes `trace` to trace execution of an example program `data/test`.

```
[me@centos8 pal-tools]$ gcc -gdwarf-4 -O0 data/test.c -odata/test
[me@centos8 pal-tools]$ cat data/test.c
int main(int argc, char **argv)
{
    int a = 0;
    switch (argc) {
        case 1:
        case 2:
        a = argc;
        break;
        default:
        a = -1;
        break;
    }
    return a;
}
[me@centos8 pal-tools]$ ./trace -- data/test
/home/me/work/pal-tools/data/test.c:9
/home/me/work/pal-tools/data/test.c:4
/home/me/work/pal-tools/data/test.c:5
/home/me/work/pal-tools/data/test.c:6
/home/me/work/pal-tools/data/test.c:7
/home/me/work/pal-tools/data/test.c:13
/home/me/work/pal-tools/data/test.c:14
/home/me/work/pal-tools/data/test.c:2
/home/me/work/pal-tools/data/test.c:8
/home/me/work/pal-tools/data/test.c:3
```

Here is a debug trace showing which lines are in the final trace. If you want this kind of trace, you can use `trace -lDEBUG -- data/test` and it will be printed at the end.

```
DEBUG - /home/me/work/pal-tools/data/test.c
DEBUG -    2 {
DEBUG -    3     int a = 0;
DEBUG -    4     switch (argc) {
DEBUG -    5         case 1:
DEBUG -    6         case 2:
DEBUG -    7         a = argc;
DEBUG -    8         break;
DEBUG -    9         default:
DEBUG -   13     return a;
DEBUG -   14 }
```

## Include paths

Sometimes Clang cannot fully parse a file if it cannot find the headers that file includes.
It may miss some variable declarations that are in the file, and in some cases it will not be able to parse it at all (no static information would be added).
In this case, you can specify an include path the same way you do for Clang, with the `-I` flag.

In this example, giving the include path `-Itools/trace/tests/hidden` allows Clang to find the missing header and adds the variable declaration at line 5.

```
[me@centos8 pal-tools]$ gcc -gdwarf-4 -O0 tools/trace/tests/includeme.c -otools/trace/tests/includeme -Itools/trace/tests/hidden
[me@centos8 pal-tools]$ cat -n tools/trace/tests/includeme.c
     1  #include <includeme.h>
     2
     3  int main()
     4  {
     5      mytype i;
     6      i = 0;
     7      i--;
     8      return i;
     9  }
[me@centos8 pal-tools]$ # Line numbers are sorted in the printout for ease of reading
[me@centos8 pal-tools]$ # Observe that line 5 is added when the include path is provided with -I
[me@centos8 pal-tools]$ ./trace -- tools/trace/tests/includeme | sort
/home/me/work/pal-tools/tools/trace/tests/includeme.c:4
/home/me/work/pal-tools/tools/trace/tests/includeme.c:6
/home/me/work/pal-tools/tools/trace/tests/includeme.c:7
/home/me/work/pal-tools/tools/trace/tests/includeme.c:8
/home/me/work/pal-tools/tools/trace/tests/includeme.c:9
[me@centos8 pal-tools]$ ./trace -Itools/trace/tests/hidden -- tools/trace/tests/includeme | sort
/home/me/work/pal-tools/tools/trace/tests/includeme.c:4
/home/me/work/pal-tools/tools/trace/tests/includeme.c:5
/home/me/work/pal-tools/tools/trace/tests/includeme.c:6
/home/me/work/pal-tools/tools/trace/tests/includeme.c:7
/home/me/work/pal-tools/tools/trace/tests/includeme.c:8
/home/me/work/pal-tools/tools/trace/tests/includeme.c:9
```

## Source prefixes

Some projects link with libraries which we want to trace as well.
`trace` automatically filters all locations to filepaths which begin with a known prefix.
The default known prefixes are `/home` and `/root`.
Custom prefixes can be specified with the option `--include_source_prefix`.
Keep in mind, this will clear the defaults `/home` and `/root`, so if you want to keep these, you should specify them as well.

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
