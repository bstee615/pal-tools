int main(int argc, char **argv)
{
    int a = 0;
    switch (argc) {
        case 1:
        case 2:
        a = argc;
        break;
        default:
        a = -1;
        break;
    }
    return a;
}