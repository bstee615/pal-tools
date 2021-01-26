# Download Pin 3.16
if [ -z "$1" ]
then
    rename_to='pin-3.16'
else
    rename_to="$(basename $1)"
fi

pin_url='https://software.intel.com/sites/landingpage/pintool/downloads/pin-3.16-98275-ge0db48c31-gcc-linux.tar.gz'
tools="$rename_to/source/tools"
if [ ! -d $rename_to ]
then
    # Download and unzip Pin
    echo Downloading and unpacking from $pin_url...
    wget -qO- $pin_url | tar --transform "s/^pin-3.16-98275-ge0db48c31-gcc-linux/$rename_to/" -xvz
    if [ ! $? -eq 0 -a -d $rename_to ]
    then
        echo Could not download Pin from $pin_url to $rename_to.
        exit 1
    fi
    # Delete all tools except the support necessary for trace-pintool
    ls -d $tools/* | grep -v -e trace-pintool -e Config -e Utils -e makefile | xargs rm -r
else
    echo Pin already exists at $rename_to.
fi

# Clone trace-pintool
trace_url='https://github.com/bstee615/trace-pintool'
trace_tool="$tools/trace-pintool"
if [ ! -d $trace_tool ]
then
    echo Cloning pintool repo at $trace_tool...
    git clone $trace_url $trace_tool
    if [ ! $? -eq 0 -a -d $trace_tool ]
    then
        echo echo Could not clone trace-pintool from $trace_url to $trace_tool.
        exit 1
    fi
else
    echo Pintool already exists at $trace_tool.
fi

# Make trace-pintool
pushd $trace_tool
make
make_ret=$?
popd
if [ ! $make_ret -eq 0 ]
then
    echo Could not build Pin. Please cd to $trace_tool and run make.
    exit 1
else
    echo make completed successfully.
fi
