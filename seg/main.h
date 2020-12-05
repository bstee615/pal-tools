#ifndef MAIN_H
#define MAIN_H

struct f
{
    int x;
    unsigned int y;
    char c;
    char *cp;
};

int helium_sum(int x, unsigned int y);
int helium_body(struct f *myf);

#endif // MAIN_H