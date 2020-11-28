#include <stdio.h>

struct f
{
    int x;
    char c;
    char **cp;
};

int sum(struct f *myf, char y);

int main()
{
    struct f myf;
    myf.x = 3;
    int s = sum(&myf, 4);
    printf("Hello, world! %d\n", s);
}

int sum(struct f *myf, char y)
{
    int a = myf->x + y;
    return a;
}
