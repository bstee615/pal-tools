# Harn: A C test harness generator

Run with `python3 harn.py` or the convenience command provided, `harn`.
Docs provided in `harn -h`.

Given a target function, harn generates a test harness that reads input variables from stdin and passes them to the target function.
The harness reads one value per line.
See examples of reading ints, characters, and strings below.

# Requirements

- `clang`
- `clang-format`
- Python libclang wrapper: `pip3 install libclang`

# Example

`main.c` is an example program with two functions, `sum` and `body`.
See how harn generates a test harness for them.

## `sum()`

```
$ cat main.c
#include <stdio.h>

struct f
{
    int x;
    unsigned int y;
    char c;
    char *cp;
};

int sum(int x, unsigned int y);
int body(struct f *myf);

int body(struct f *myf)
{
    printf("params: %d %u %c %s\n", myf->x, myf->y, myf->c, myf->cp);
    int z = sum(myf->x, myf->y);
    return z;
}

int sum(int x, unsigned int y)
{
    unsigned int z = x+y;
    printf("%d + %u = %u\n", x, y, z);
    return z;
}

$ ./harn main.c
//BEGIN original file
/* contents of the original file... */
//END original file

// BEGIN test harness
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
// BEGIN declare input variables
int x;
unsigned int y;
// END declare input variables

// BEGIN read input variables
// BEGIN read value for x
char *x_s=NULL;
size_t x_sn=0;
printf("x: ");
getline(&x_s, &x_sn, stdin);
x = atoi(x_s); // provided line
free(x_s);
// END read value for x
// BEGIN read value for y
char *y_s=NULL;
size_t y_sn=0;
printf("y: ");
getline(&y_s, &y_sn, stdin);
y = strtoul(y_s, NULL, 10); // provided line
free(y_s);
// END read value for y
// END read input variables

// BEGIN call into segment
sum(x, y);
// END call into segment

// BEGIN cleanup input variables

// END cleanup input variables
}
// END test harness
```

Let's check out the results.

`sum()` has two parameters, `x` and `y`.
```
int sum(int x, unsigned int y)
```

Since `x` and `y` are primitives, harn declares just one local variable for each.
```
int x;
unsigned int y;
```

Then, harn reads values for `x`.
It reads a line into a temporary variable, `x_s`, then parses `x_s` into an int.
```
char *x_s=NULL;
size_t x_sn=0;
printf("x: ");
getline(&x_s, &x_sn, stdin);
x = atoi(x_s); // provided line
free(x_s);
```

Similarly for `y`.

Finally, harn calls `sum()` with `x` and `y`.
Faults in `sum()` should be triggered given some values for x and y.
```
sum(x, y);
```

Expected output:
```
$ ./harn main.c -n sum > main_harness.c
$ clang main_harness.c 
$ ./a.out
x: -123
y: 321
-123 + 321 = 198
```

## `body()`

By default, harn targets the last function in the input file.
To target a different function, use `-n`

```
$ ./harn main.c -n body
//BEGIN original file
/* contents of the original file... */
//END original file

// BEGIN test harness
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main() {
// BEGIN declare input variables
int x;
unsigned int y;
char c;
char * cp;
struct f myf_v;
struct f * myf;
// END declare input variables

// BEGIN read input variables
// BEGIN read value for x
char *x_s=NULL;
size_t x_sn=0;
printf("x: ");
getline(&x_s, &x_sn, stdin);
x = atoi(x_s); // provided line
free(x_s);
// END read value for x
// BEGIN read value for y
char *y_s=NULL;
size_t y_sn=0;
printf("y: ");
getline(&y_s, &y_sn, stdin);
y = strtoul(y_s, NULL, 10); // provided line
free(y_s);
// END read value for y
// BEGIN read value for c
char *c_s=NULL;
size_t c_sn=0;
printf("c: ");
getline(&c_s, &c_sn, stdin);
c = c_s[0]; // provided line
free(c_s);
// END read value for c
// BEGIN read value for cp
char *cp_s=NULL;
size_t cp_sn=0;
printf("cp: ");
getline(&cp_s, &cp_sn, stdin);
cp = malloc(cp_sn);
strcpy(cp, cp_s); // provided line
free(cp_s);
// END read value for cp
// BEGIN assign fields of myf_v
myf_v.cp = cp;
myf_v.c = c;
myf_v.y = y;
myf_v.x = x;
// END assign fields of myf_v
// BEGIN assign ptr myf
myf = &myf_v;
// END assign ptr myf
// END read input variables

// BEGIN call into segment
body(myf);
// END call into segment

// BEGIN cleanup input variables
free(cp);
// END cleanup input variables
}
// END test harness
```

Now, the harness is calling `body()`.

Observe the new parameter types being handled.

`c` is a `char`, so the first character is being read in and the rest ignored.
```
char *c_s=NULL;
size_t c_sn=0;
printf("c: ");
getline(&c_s, &c_sn, stdin);
c = c_s[0]; // provided line
free(c_s);
```

`cp` is a `char *`, so is being read and copied in.
```
char *cp_s=NULL;
size_t cp_sn=0;
printf("cp: ");
getline(&cp_s, &cp_sn, stdin);
cp = malloc(cp_sn);
strcpy(cp, cp_s); // provided line
free(cp_s);
```

`struct f myf` has four fields. Each field is being read in, then assigned into the struct.
```
myf_v.cp = cp;
myf_v.c = c;
myf_v.y = y;
myf_v.x = x;
```

Finally, `myf` is a pointer. Harn handles pointers by declaring a local variable `myf_v` to hold the value of the pointer, then assigning the pointer to the reference of `myf_v`.
```
struct f myf_v;
struct f * myf;
...other initialization code...
myf = &myf_v;
```
