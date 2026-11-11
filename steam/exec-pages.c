/* SPDX-License-Identifier: MIT
 * P3S next-exec personality ABI, from our public mixed-page launcher.
 * This launches a native ELF directly; it does not invoke FEX or edit binfmt.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/personality.h>
#include <unistd.h>
#define PAGE_4K 0x40000000UL
int main(int argc, char **argv)
{
    if (argc == 1) {
        printf("{\"pages\":%lu}\n", getauxval(AT_PAGESZ));
        return 0;
    }
    if (argc < 3 || strcmp(argv[1], "--4k")) return 2;
    if (getauxval(AT_PAGESZ) != 4096) {
        int current = personality(0xffffffffUL);
        if (current < 0 || personality((unsigned)current | PAGE_4K) < 0) {
            perror("P3S next-exec 4K"); return 1;
        }
    }
    execvp(argv[2], argv + 2);
    perror("exec");
    return 1;
}
