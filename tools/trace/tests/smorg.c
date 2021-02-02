#include <stdio.h>

int smorgasboard() {
    int a = 0;
    int b = 1;
    int c = 2;

    printf("wow! %d, %d, and %d!\n", a, b, c);

    switch (a) {
        case 0:
        default:
        a = b;
        printf("huh\n");
        break;
        case 1:
        case 253:
        printf("neat\n");
        a = c;
        break;
    }
    return a;
}
