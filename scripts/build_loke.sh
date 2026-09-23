#!/bin/sh
# build_loke.sh — Build the loke native binary.
#
# This is the `loke` target of the five build targets: packages/core/src,
# packages/shared/src, packages/browser/extensions and packages/browser/pages, linked
# into a single ooke-served binary on port 11430.
#
# The compile pipeline itself — fresh ooke .tki copy, dependency-ordered interface
# pass, compile census, undefined-symbol census, link — lives in
# scripts/lib/build_tree.sh, because four other trees need exactly the same pipeline
# with a different root list and a different (or absent) link phase. See
# scripts/build_trees.sh for the other four. What stays HERE is only what is specific
# to loke: the generated handler registry and the generated ooke server main.
#
# This script reports every compile failure and exits non-zero if any module failed.
# It does NOT suppress compiler stderr and does NOT pass
# -Wl,-undefined,dynamic_lookup, because both of those turn build failures into
# runtime crashes. A failure census is written to build/break-report.txt.

set -eu

PROJECTDIR="$(cd "$(dirname "$0")/.." && pwd)"
BROWSERDIR="$PROJECTDIR/packages/browser"
OOKE_DIR="${OOKE_DIR:-$HOME/tk/toke-ooke}"
TOKE_DIR="${TOKE_DIR:-$HOME/tk/toke}"

# Step 0: Toolchain guard — refuse to compile against an unverified toolchain
if [ -x "$PROJECTDIR/scripts/check_toolchain.sh" ]; then
  TOKE_DIR="$TOKE_DIR" OOKE_DIR="$OOKE_DIR" "$PROJECTDIR/scripts/check_toolchain.sh"
fi

# Step 1: Generate _serve_main.tk
# NOTE: match arms use $ok/$err and serverun's final parameter is [str] as of
# ooke 2.0.0. Keep this in sync with $OOKE_DIR/src/ooke.serve.tki.
cat > "$BROWSERDIR/_serve_main.tk" << 'MAIN'
(* Copyright 2026 loke contributors
   SPDX-License-Identifier: Apache-2.0 *)

m=app.main;
i=http:std.http;
i=log:std.log;
i=str:std.str;
i=path:std.path;
i=args:std.args;
i=config:ooke.config;
i=serve:ooke.serve;
i=handlers:ooke.handlers;

(* ooke.config exports configload and nothing else: cfgdefault is named in ooke's own
   cli.tkc.md as BLOCKED on a toke codegen bug and is not in ooke.config.tki. Calling
   it produced an undefined `_ooke_config_cfgdefault` at link time, which is the only
   place it was reported. The fallback config is built here instead, from the field
   list in ooke.config.tki. loke's own server port is 11430. *)
f=lokedefaultcfg():$ookecfg{
  <$ookecfg{
    sitename:"loke";
    siteurl:"http://127.0.0.1:11430";
    sitelanguage:"en-AU";
    buildoutput:"build";
    buildminify:false;
    buildinlinecss:false;
    serverport:11430;
    serverworkers:4;
    servercorsorigins:"";
    storebackend:"sqlite";
    logaccessformat:"combined";
    logmaxlines:100000;
    logmaxagedays:30;
    apiprefix:"/api"
  }
};

f=main():i64{
  let projectdir=mt args.get(1 as u64) {$ok:v v;$err:e "."};
  let cfg=mt config.configload(path.join(projectdir;"ooke.toml")) {$ok:v v;$err:e lokedefaultcfg()};
  let handledpaths=handlers.registerall();
  (log.info(str.concat("registered ";str.concat(str.fromint(handledpaths.len);" handler routes"));@()));
  let r=mt serve.serverun(projectdir;cfg.serverport;cfg.serverworkers;cfg.buildoutput;"";"";cfg.sitename;cfg.siteurl;cfg.sitelanguage;cfg.apiprefix;cfg.servercorsorigins;handledpaths) {$ok:v 0;$err:e 1};
  <r
};
MAIN

# Step 2: the tree build.
#
# The interface dir and the object dir are pinned to the paths they have always had:
# scripts/run_tests.sh reads build/interfaces for -I and archives
# packages/browser/build/ooke into libloke.a, so moving either would break the test
# suite silently. The other four targets write under build/trees/<name>/ instead,
# which is also why the link line names its object dirs explicitly now — the old
# single `find build -name '*.o'` sweep would have put another target's objects on
# loke's link line and duplicated every symbol in core.
#
# --legacy-report keeps build/break-report.txt where CI uploads it from and where
# scripts/build_census.py looks when no --tree is given.
exec "$PROJECTDIR/scripts/lib/build_tree.sh" \
  --link=binary \
  --main="$BROWSERDIR/_serve_main.tk" \
  --binary="$BROWSERDIR/build/loke" \
  --iface="$PROJECTDIR/build/interfaces" \
  --objdir="$BROWSERDIR/build/ooke" \
  --report="$PROJECTDIR/build/trees/loke/break-report.txt" \
  --legacy-report="$PROJECTDIR/build/break-report.txt" \
  --gen-handlers="$BROWSERDIR/pages:$BROWSERDIR/_handlers.tk" \
  --extra="$BROWSERDIR/_handlers.tk:handlers" \
  --handler-iface-pass="$BROWSERDIR/pages" \
  --ooke-objs \
  loke \
  "$PROJECTDIR/packages/core/src" \
  "$PROJECTDIR/packages/shared/src" \
  "$BROWSERDIR/extensions" \
  "$BROWSERDIR/pages"
