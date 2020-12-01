#include <stdio.h>

struct f
{
    int x;
    unsigned int y;
    char c;
    char *cp;
};

int sum(struct f *myf);

int sum(struct f *myf)
{
    printf("%d %u %c %s\n", myf->x, myf->y, myf->c, myf->cp);
    int a = myf->x;
    return a;
}
