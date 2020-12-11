# mirror.py

Capture fault signature input from program input.
The original program's failure inducing input is provided as a program input.
Not all fault signatures will begin at the entry point.
We need to capture the state of all input variables at the beginning of the fault signature's path,
when running the original program with the failure inducing program input.
