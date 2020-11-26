#include <stdio.h>

int sum(int x, char y)
{
    int a = x + y;
    return a;
}

int main()
{
    int s = sum(3, 4);
    printf("Hello, world! %d\n", s);
}
