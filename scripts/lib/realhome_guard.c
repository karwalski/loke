/* Copyright 2026 loke contributors
   SPDX-License-Identifier: Apache-2.0

   realhome_guard.c — F3b.13. Records every filesystem call a test binary makes into the
   developer's REAL ~/.loke.

   run_tests.sh gives each test binary a throwaway HOME, so std.homedir(), proc.homedir()
   and os.getenv("HOME") all resolve under it. That alone is a convention: a test that
   hardcoded the real path, or a runtime that fell back to getpwuid(), would still reach the
   developer's config.toml, settings.json, loke.db or memory palace, and nothing would say
   so. This makes it observable. It is injected with DYLD_INSERT_LIBRARIES and interposes
   the libc calls a read or a write has to go through (open, fopen, stat, access, opendir,
   mkdir, unlink, rename, ...). A call whose path is LOKE_GUARD_PREFIX, or under it, is
   appended to LOKE_GUARD_LOG as "<call> <path>". The call itself still proceeds: the guard
   reports, it does not change what the test observes, so a test that fails under it fails
   for the reason it would have failed anyway. run_tests.sh fails the test (and the run)
   when the log is non-empty.

   It only sees paths passed to libc. Keychain access goes through securityd over IPC and
   is not a path at all, so it is invisible here; see the X8.7 note in run_tests.sh. */
#include <dirent.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int under_prefix(const char *path) {
  const char *prefix = getenv("LOKE_GUARD_PREFIX");
  if (!prefix || !*prefix || !path) return 0;
  size_t n = strlen(prefix);
  if (strncmp(path, prefix, n) != 0) return 0;
  return path[n] == '\0' || path[n] == '/';
}

static void record(const char *call, const char *path) {
  if (!under_prefix(path)) return;
  const char *log = getenv("LOKE_GUARD_LOG");
  if (!log || !*log) return;
  /* Calls made from inside this image are not interposed, so this is the real open. */
  int fd = open(log, O_WRONLY | O_CREAT | O_APPEND, 0600);
  if (fd < 0) return;
  char line[4096];
  int len = snprintf(line, sizeof line, "%s %s\n", call, path);
  if (len > 0) write(fd, line, (size_t)len < sizeof line ? (size_t)len : sizeof line - 1);
  close(fd);
}

static int g_open(const char *path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) {
    va_list ap;
    va_start(ap, flags);
    mode = (mode_t)va_arg(ap, int);
    va_end(ap);
  }
  record("open", path);
  return open(path, flags, mode);
}
static int g_openat(int dirfd, const char *path, int flags, ...) {
  mode_t mode = 0;
  if (flags & O_CREAT) {
    va_list ap;
    va_start(ap, flags);
    mode = (mode_t)va_arg(ap, int);
    va_end(ap);
  }
  record("openat", path);
  return openat(dirfd, path, flags, mode);
}
/* fopen and realpath each have two exported names, and which one a caller binds to depends
   on the feature macros it was compiled with (_DARWIN_C_SOURCE selects the $DARWIN_EXTSN
   variant). Both are interposed, or a caller built one way would pass unseen. */
FILE *fopen_plain(const char *, const char *) __asm("_fopen");
FILE *fopen_ext(const char *, const char *) __asm("_fopen$DARWIN_EXTSN");
char *realpath_plain(const char *, char *) __asm("_realpath");
char *realpath_ext(const char *, char *) __asm("_realpath$DARWIN_EXTSN");
static FILE *g_fopen(const char *path, const char *mode) { record("fopen", path); return fopen_plain(path, mode); }
static FILE *g_fopen_ext(const char *path, const char *mode) { record("fopen", path); return fopen_ext(path, mode); }
static FILE *g_freopen(const char *path, const char *mode, FILE *f) { record("freopen", path); return freopen(path, mode, f); }
static int g_stat(const char *path, struct stat *st) { record("stat", path); return stat(path, st); }
static int g_lstat(const char *path, struct stat *st) { record("lstat", path); return lstat(path, st); }
static int g_fstatat(int d, const char *path, struct stat *st, int fl) { record("fstatat", path); return fstatat(d, path, st, fl); }
static int g_access(const char *path, int m) { record("access", path); return access(path, m); }
static int g_faccessat(int d, const char *path, int m, int fl) { record("faccessat", path); return faccessat(d, path, m, fl); }
static DIR *g_opendir(const char *path) { record("opendir", path); return opendir(path); }
static int g_mkdir(const char *path, mode_t m) { record("mkdir", path); return mkdir(path, m); }
static int g_mkdirat(int d, const char *path, mode_t m) { record("mkdirat", path); return mkdirat(d, path, m); }
static int g_rmdir(const char *path) { record("rmdir", path); return rmdir(path); }
static int g_unlink(const char *path) { record("unlink", path); return unlink(path); }
static int g_unlinkat(int d, const char *path, int fl) { record("unlinkat", path); return unlinkat(d, path, fl); }
static int g_remove(const char *path) { record("remove", path); return remove(path); }
static int g_rename(const char *a, const char *b) { record("rename", a); record("rename", b); return rename(a, b); }
static int g_truncate(const char *path, off_t n) { record("truncate", path); return truncate(path, n); }
static int g_chmod(const char *path, mode_t m) { record("chmod", path); return chmod(path, m); }
static char *g_realpath(const char *path, char *out) { record("realpath", path); return realpath_plain(path, out); }
static char *g_realpath_ext(const char *path, char *out) { record("realpath", path); return realpath_ext(path, out); }

#define INTERPOSE(repl, orig) \
  __attribute__((used)) static struct { const void *r; const void *o; } interpose_##orig \
  __attribute__((section("__DATA,__interpose"))) = { (const void *)(unsigned long)&repl, (const void *)(unsigned long)&orig }

INTERPOSE(g_open, open);
INTERPOSE(g_openat, openat);
INTERPOSE(g_fopen, fopen_plain);
INTERPOSE(g_fopen_ext, fopen_ext);
INTERPOSE(g_freopen, freopen);
INTERPOSE(g_stat, stat);
INTERPOSE(g_lstat, lstat);
INTERPOSE(g_fstatat, fstatat);
INTERPOSE(g_access, access);
INTERPOSE(g_faccessat, faccessat);
INTERPOSE(g_opendir, opendir);
INTERPOSE(g_mkdir, mkdir);
INTERPOSE(g_mkdirat, mkdirat);
INTERPOSE(g_rmdir, rmdir);
INTERPOSE(g_unlink, unlink);
INTERPOSE(g_unlinkat, unlinkat);
INTERPOSE(g_remove, remove);
INTERPOSE(g_rename, rename);
INTERPOSE(g_truncate, truncate);
INTERPOSE(g_chmod, chmod);
INTERPOSE(g_realpath, realpath_plain);
INTERPOSE(g_realpath_ext, realpath_ext);
