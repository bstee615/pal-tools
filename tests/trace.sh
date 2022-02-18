#!/bin/bash

root_dir="$(dirname $(dirname $(realpath $0)))"

source "$root_dir/tests/assert.sh"

function error() {
    echo $@
    exit 1
}

gcc -gdwarf-2 -O0 "data/test.c" -o "data/test" || error "Could not compile"
"$root_dir/trace" --clang_library_file /usr/lib64/libclang.so.13 -- "data/test" &>/dev/null
assert_eq "$?" "0" "Trace exited with error"
"$root_dir/trace" --clang_library_file /usr/lib64/libclang.so.13 -- "data/no-file-here" &>/dev/null
assert_not_eq "$?" "0" "Trace did not exit with error on a missing file"

function run_trace() {
    exe_file="$1"
    shift 1
    "$root_dir/trace" --clang_library_file /usr/lib64/libclang.so.13 $@ -- "$exe_file"
    return "$?"
}

gcc -gdwarf-2 -O0 "data/loops.c" -o "data/loops" || error "Could not compile"

# There are no duplicates in the trace
assert_eq "$(run_trace data/loops 2>&1 | wc -l)" \
    "$(run_trace data/loops 2>&1 | uniq | wc -l)" \
    "There should be no duplicates in the line-only trace!"
assert_eq "$(run_trace data/loops --include_column 2>&1 | wc -l)" \
    "$(run_trace data/loops --include_column 2>&1 | uniq | wc -l)" \
    "There should be no duplicates in the line/column trace!"

# Loop bodies are executed and logged the correct number of times
output="$(run_trace data/loops)"
assert_eq "$(printf "%s" "$output" | grep "loops.c:5" | wc -l)" \
    "10" \
    "The do/while loop should be executed and logged 10 times"
assert_eq "$(printf "%s" "$output" | grep "loops.c:9" | wc -l)" \
    "10" \
    "The for loop should be executed and logged 10 times"
assert_eq "$(printf "%s" "$output" | grep "loops.c:13" | wc -l)" \
    "10" \
    "The while loop should be executed and logged 10 times"
assert_eq "$(printf "%s" "$output" | grep "loops.c:19" | wc -l)" \
    "1" \
    "The switch should be executed and logged 1 time"
