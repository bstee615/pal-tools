#!/bin/bash

tmp_dir=`mktemp -d -t trace-test-XXXXXXXXXX`
cp install.sh $tmp_dir
for arg in "" "$tmp_dir/foo"
do
    pushd $tmp_dir
        # Invoke command
        bash -x install.sh $arg
        # Check output
        if [ $? -eq 0 ]; then
            echo SUCCESSFULLY INSTALLED
        else
            echo FAILED TO INSTALL. args="$arg". Check out $tmp_dir for details. && exit 1
        fi
    popd
done
rm -rf $tmp_dir
