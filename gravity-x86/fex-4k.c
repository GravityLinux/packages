// SPDX-License-Identifier: MIT
/*
 * binfmt_misc handler (POCF) for x86 programs on P3S kernels: run them through
 * FEXInterpreter with 4K pages.
 *
 * binfmt passes [handler, filename, original argv0, args...] and the opened
 * executable as AT_EXECFD. From a 16K caller we request 4K pages for the next
 * exec and re-execute ourselves to see whether the kernel granted them. With
 * 4K pages we start FEXInterpreter on the executable's pathname, which the 4K
 * request is inherited by. FEX takes no separate argv0, so the guest's argv0
 * is that pathname.
 *
 * Otherwise (no P3S, privileged launches, no AT_EXECFD) binfmt-dispatcher gets
 * the launch exactly as binfmt gave it to us and keeps its muvm behaviour. It
 * is not used on the 4K path: it reads the executable from fd 3, which is a
 * stale descriptor when one guest execs another, and it passes FEX the
 * filename and original argv0 as extra guest arguments.
 */
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <sys/personality.h>
#include <unistd.h>

#define ADDR_PAGE_SIZE_4KB 0x40000000UL
#define DISPATCHER "/usr/bin/binfmt-dispatcher"
#define FEX "/usr/bin/FEXInterpreter"
#define STAGE2 "--p3s-execfd"

static int dispatch(char **argv)
{
	int old = personality(0xffffffffUL);
	if (old != -1)
		personality((unsigned int)old & ~ADDR_PAGE_SIZE_4KB);
	argv[0] = DISPATCHER;
	execv(DISPATCHER, argv);
	perror("fex-4k: exec " DISPATCHER);
	return 126;
}

/* argv is binfmt's vector: [handler, filename, original argv0, args...]. */
static int run_fex(int fd, int argc, char **argv)
{
	char link[64], path[PATH_MAX];
	snprintf(link, sizeof(link), "/proc/self/fd/%d", fd);
	ssize_t len = readlink(link, path, sizeof(path) - 1);
	if (len <= 0 || path[0] != '/') {
		fprintf(stderr, "fex-4k: cannot resolve the executable's pathname\n");
		return 126;
	}
	path[len] = '\0';
	close(fd);

	char **fex_argv = calloc(argc + 1, sizeof(*fex_argv));
	if (!fex_argv)
		return 126;
	int n = 0;
	fex_argv[n++] = FEX;
	fex_argv[n++] = path;
	for (int i = 3; i < argc; i++)
		fex_argv[n++] = argv[i];
	execv(FEX, fex_argv);
	perror("fex-4k: exec " FEX);
	return 126;
}

int main(int argc, char **argv)
{
	if (argc >= 3 && !strcmp(argv[1], STAGE2)) {
		int fd = atoi(argv[2]);
		argv += 3;
		argc -= 3;
		if (getauxval(AT_PAGESZ) == 4096)
			return run_fex(fd, argc, argv);
		return dispatch(argv);
	}

	errno = 0;
	unsigned long fd = getauxval(AT_EXECFD);
	if (errno || argc < 3 || getauxval(AT_SECURE))
		return dispatch(argv);
	if (getauxval(AT_PAGESZ) == 4096)
		return run_fex((int)fd, argc, argv);

	int old = personality(0xffffffffUL);
	if (old == -1 || personality((unsigned int)old | ADDR_PAGE_SIZE_4KB) == -1)
		return dispatch(argv);
	char fdarg[16];
	snprintf(fdarg, sizeof(fdarg), "%lu", fd);
	char **stage2 = calloc(argc + 4, sizeof(*stage2));
	if (!stage2)
		return 126;
	stage2[0] = "fex-4k";
	stage2[1] = STAGE2;
	stage2[2] = fdarg;
	memcpy(stage2 + 3, argv, argc * sizeof(*argv));
	execv("/proc/self/exe", stage2);
	return dispatch(argv);
}
