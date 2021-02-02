
int boo() {
    int boo_var = 0;
    switch (boo_var) {
        default: // boo
        boo_var = 20;
    }
    return boo_var;
}

int foo() {
    int foo_var = 12;
    switch(foo_var) {
        case 12: // foo
        return 10;
        default: // foo
        return -1;
    }
    return 10;
}
