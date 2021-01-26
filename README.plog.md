# plog.py

Capture code segment input from program input.
The original program's failure inducing input is provided as a program input.
Not all code segments will begin at the entry point.
We need to capture the state of all input variables at the beginning of the code segment's path,
when running the original program with the failure inducing program input.
