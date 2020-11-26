#include <stdio.h>

struct f
{
    int x;
    char c;
}

int sum(struct f myf, char y)
{
    int a = myf.x + y;
    return a;
}

int main()
{
    struct f myf;
    myf.x = 3;
    int s = sum(3, 4);
    printf("Hello, world! %d\n", s);
}
