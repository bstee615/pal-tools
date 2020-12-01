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
