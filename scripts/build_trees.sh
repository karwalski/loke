#!/bin/sh
# build_trees.sh — the five build targets, in one place (stories F10.23a-c).
#
# Why this exists
# ---------------
# Before F10.23 this repo compiled exactly four roots: packages/core/src,
# packages/shared/src, packages/browser/extensions and packages/browser/pages. 218
# modules, green, 0 errors. 247 non-test .tk files in six other trees had never been
# compiled once, so "the build is green" was true and also said nothing about most of
# the code in the repository. Measured cold those 247 files cost 951 errors — and
# about a third of that was not a defect but the absence of a per-tree interface pass:
# packages/cli had eleven "module 'cli.output' not found" errors for its own sibling.
#
# This makes the cliff measurable and ratcheted, so trees can be onboarded one at a
# time without ever letting a green tree regress. Adding a tree to the shipped build
# is a LATER story; this is the instrument.
#
# The five targets
# ----------------
#   loke         core/src shared/src browser/extensions browser/pages   -> binary
#                (delegated to scripts/build_loke.sh, which owns the generated
#                 handler registry and the generated ooke server main for port 11430)
#   loke-cli     core/src shared/src cli/src mcp-broker/src mcp-toke/src -> binary
#   moke         core/src shared/src mcp-toke/src moke/{src,data,extensions,pages}
#                                                                        -> ooke binary
#   src-legacy   src/                                                   -> CHECK ONLY
#   browser-app  packages/browser/src                                   -> CHECK ONLY
#
# Two of them must not link, and that is a property of the code, not a shortcut:
#   * src-legacy has no entry point. Its 102 modules are the pre-monorepo tree and
#     several of them are superseded by packages/core; linking them would be a claim
#     about which copy is current, which this script has no business making.
#   * browser-app cannot link at all. packages/browser/src/shell.tk imports
#     std.webview, and toke's stdlib has no webview.tki. That is an upstream ask;
#     reporting it as a broken tree would send someone to edit loke for a week.
#
# What it measures / does not measure
# -----------------------------------
# Per target: interfaces emitted, modules compiled, every diagnostic (to
# build/trees/<name>/break-report.txt), undefined symbols attributed to the calling
# module, and whether the link succeeds. It does NOT measure correctness, does not run
# tests, and a tree at zero errors has only been type-checked.
#
# Usage
# -----
#   scripts/build_trees.sh                 # list the targets and their state
#   scripts/build_trees.sh loke-cli        # build one target
#   scripts/build_trees.sh --all           # every target, continuing past failures
#   scripts/build_trees.sh --probe moke    # add the per-module link probe (slow)
#   scripts/build_trees.sh --baseline --all    # build, then baseline every target
#
# Exit status: the number of targets that failed, so 0 means every target met its own
# bar (compiled clean, and linked if it is a linking target).

set -u

PROJECTDIR="$(cd "$(dirname "$0")/.." && pwd)"
LIB="$PROJECTDIR/scripts/lib/build_tree.sh"
CENSUS="$PROJECTDIR/scripts/build_census.py"
TREES="loke loke-cli moke src-legacy browser-app"

[ -x "$LIB" ] || { echo "ERROR: $LIB missing or not executable" >&2; exit 1; }
[ -f "$CENSUS" ] || { echo "ERROR: $CENSUS missing" >&2; exit 1; }

PROBE=
BASELINE=0
KEEP_GOING=--keep-going
WANT=

while [ $# -gt 0 ]; do
  case "$1" in
    --all)        WANT="$TREES" ;;
    --probe)      PROBE=--probe ;;
    --baseline)   BASELINE=1 ;;
    --strict-compile) KEEP_GOING= ;;
    --help|-h)    sed -n '1,60p' "$0"; exit 0 ;;
    --*)          echo "ERROR: unknown option $1" >&2; exit 1 ;;
    *)            WANT="$WANT $1" ;;
  esac
  shift
done

if [ -z "$(echo "$WANT" | tr -d ' ')" ]; then
  echo "targets: $TREES"
  echo ""
  printf '%-14s %-9s %-9s %s\n' TARGET ERRORS UNDEF BASELINE
  for t in $TREES; do
    d="$PROJECTDIR/build/trees/$t"
    e="-"; u="-"; b="-"
    [ -f "$d/break-report.txt" ] && e=$(python3 -c "
import json,sys
n=0
for l in open('$d/break-report.txt'):
    l=l.strip()
    if l.startswith('{') and json.loads(l).get('severity')=='error': n+=1
print(n)" 2>/dev/null || echo '?')
    [ -f "$d/symbol-census.json" ] && u=$(python3 -c "
import json;print(json.load(open('$d/symbol-census.json')).get('undefined_symbols'))" 2>/dev/null || echo '?')
    [ -f "$d/census-baseline.json" ] && b=$(python3 -c "
import json;print(json.load(open('$d/census-baseline.json'))['total'])" 2>/dev/null || echo '?')
    printf '%-14s %-9s %-9s %s\n' "$t" "$e" "$u" "$b"
  done
  echo ""
  echo "Run: scripts/build_trees.sh --all   (or one target name)"
  exit 0
fi

FAILURES=0

build_one() {
  _t=$1
  echo ""
  echo "════════════════════════════════════════════════════════════════════"
  echo " $_t"
  echo "════════════════════════════════════════════════════════════════════"
  case "$_t" in

  loke)
    # Delegated: build_loke.sh owns the generated handler registry and the generated
    # ooke server main, and scripts/run_tests.sh depends on its interface and object
    # directories staying where they are.
    "$PROJECTDIR/scripts/build_loke.sh"
    ;;

  loke-cli)
    # packages/cli/src/main.tk declares f=main(args:@str):i32, so this tree has a real
    # entry point. mcp-broker/src/main.tk and mcp-toke/src/main.tk declare one too;
    # all three emit a `_main` and the link would fail on duplicate symbols, so the
    # other two are compiled and censused but kept off the link line. Excluding them
    # from the CHECK instead would hide whatever is wrong inside them.
    "$LIB" $KEEP_GOING $PROBE \
      --link=binary \
      --main="$PROJECTDIR/packages/cli/src/main.tk" \
      --binary="$PROJECTDIR/build/trees/loke-cli/loke-cli" \
      --no-link=cli_main --no-link=mcpbroker_main --no-link=mcptoke_main \
      loke-cli \
      "$PROJECTDIR/packages/core/src" \
      "$PROJECTDIR/packages/shared/src" \
      "$PROJECTDIR/packages/cli/src" \
      "$PROJECTDIR/packages/mcp-broker/src" \
      "$PROJECTDIR/packages/mcp-toke/src"
    ;;

  moke)
    # moke is a second ooke application: its own packages/moke/ooke.toml, its own
    # port (11432), its own pages. Two things it does NOT get here:
    #
    #   * gen_handlers.sh is NOT run over packages/moke/pages by default.
    #     packages/moke/src/_handlers.tk is a TRACKED source file that another story
    #     owns, and regenerating it on every census would put this script in the
    #     business of editing toke sources. Set LOKE_GEN_MOKE_HANDLERS=1 to run it.
    #   * the generated server main is written under build/, not into packages/moke/,
    #     for the same reason — moke has no checked-in _serve_main.tk and this script
    #     is not the place to add one.
    #
    # packages/mcp-toke/src is in the roots because packages/moke/src/mcp imports
    # mcptoke.tools; without it that import has no interface and reports as a defect
    # in moke. mcp-toke's own main IS excluded from the link (it declares f=main and
    # would collide with the generated one); packages/moke/src/main.tk is not, because
    # it declares f=start and emits no `_main` — excluding it would have made
    # moke.main.start unlinkable for no reason.
    _mokemain="$PROJECTDIR/build/trees/moke/_serve_main.tk"
    mkdir -p "$PROJECTDIR/build/trees/moke"
    write_ooke_main "$_mokemain" moke 11432 "http://127.0.0.1:11432"
    _genh=
    if [ "${LOKE_GEN_MOKE_HANDLERS:-0}" = 1 ]; then
      _genh="--gen-handlers=$PROJECTDIR/packages/moke/pages:$PROJECTDIR/packages/moke/src/_handlers.tk"
    fi
    "$LIB" $KEEP_GOING $PROBE $_genh \
      --link=binary \
      --main="$_mokemain" \
      --binary="$PROJECTDIR/build/trees/moke/moke" \
      --handler-iface-pass="$PROJECTDIR/packages/moke/pages" \
      --no-link=mcptoke_main \
      --ooke-objs \
      moke \
      "$PROJECTDIR/packages/core/src" \
      "$PROJECTDIR/packages/shared/src" \
      "$PROJECTDIR/packages/mcp-toke/src" \
      "$PROJECTDIR/packages/moke/src" \
      "$PROJECTDIR/packages/moke/data" \
      "$PROJECTDIR/packages/moke/extensions" \
      "$PROJECTDIR/packages/moke/pages"
    ;;

  src-legacy)
    # CHECK ONLY. No entry point, and several of these 102 modules are superseded by
    # packages/core — linking them would assert which copy is current.
    # packages/shared/src is an --iface-root, not a root: src/ imports shared.log, and
    # without that interface every importer reports a "module not found" that is not a
    # defect in src/. Its own errors are counted; shared's are not.
    "$LIB" $KEEP_GOING $PROBE \
      --link=none \
      --iface-root="$PROJECTDIR/packages/shared/src" \
      src-legacy \
      "$PROJECTDIR/src"
    ;;

  browser-app)
    # CHECK ONLY, and it will not link even when it is clean: browser.shell imports
    # std.webview and toke's stdlib has no webview.tki. See UPSTREAM.md.
    # shared/src, core/src and browser/pages are --iface-roots: these 13 files import
    # shared.log and twenty page.* modules, so without their interfaces the count
    # would be twenty absences rather than thirteen files' worth of real state.
    "$LIB" $KEEP_GOING $PROBE \
      --link=none \
      --iface-root="$PROJECTDIR/packages/shared/src" \
      --iface-root="$PROJECTDIR/packages/core/src" \
      --iface-root="$PROJECTDIR/packages/browser/pages" \
      browser-app \
      "$PROJECTDIR/packages/browser/src"
    ;;

  *)
    echo "ERROR: unknown target '$_t' (known: $TREES)" >&2
    return 1
    ;;
  esac
}

# The ooke server main, generated per application. Kept in sync with
# $OOKE_DIR/src/ooke.serve.tki: match arms use $ok/$err and serverun's final
# parameter is [str] as of ooke 2.0.0. ooke.config exports configload and nothing
# else — cfgdefault is named in ooke's own cli.tkc.md as BLOCKED on a toke codegen
# bug and is not in ooke.config.tki, so calling it produced an undefined
# `_ooke_config_cfgdefault` at link time and the fallback is built here instead.
# ooke 3.0.0-rc.2 (F10.39): $ookecfg gains serverhost and drops rc.1's storebackend,
# logmaxlines and logmaxagedays, and serverun takes the host after projectdir. See the
# same note in scripts/build_loke.sh.
write_ooke_main() {
  _out=$1; _site=$2; _port=$3; _url=$4
  cat > "$_out" << MAIN
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

f=appdefaultcfg():\$ookecfg{
  <\$ookecfg{
    sitename:"$_site";
    siteurl:"$_url";
    sitelanguage:"en-AU";
    buildoutput:"build";
    buildminify:false;
    buildinlinecss:false;
    serverport:$_port;
    serverhost:"127.0.0.1";
    serverworkers:4;
    servercorsorigins:"";
    logaccess:"-";
    logerror:"";
    logaccessformat:"combined";
    tlscert:"";
    tlskey:"";
    apiprefix:"/api"
  }
};

f=main():i64{
  let projectdir=mt args.get(1 as u64) {\$ok:v v;\$err:e "."};
  let cfg=mt config.configload(path.join(projectdir;"ooke.toml")) {\$ok:v v;\$err:e appdefaultcfg()};
  let handledpaths=handlers.registerall();
  (log.info(str.concat("registered ";str.concat(str.fromint(handledpaths.len);" handler routes"));@()));
  let r=mt serve.serverun(projectdir;cfg.serverhost;cfg.serverport;cfg.serverworkers;cfg.buildoutput;"";"";cfg.sitename;cfg.siteurl;cfg.sitelanguage;cfg.apiprefix;cfg.servercorsorigins;handledpaths) {\$ok:v 0;\$err:e 1};
  <r
};
MAIN
}

for t in $WANT; do
  if build_one "$t"; then
    echo "[$t] target OK"
  else
    echo "[$t] target FAILED" >&2
    FAILURES=$((FAILURES + 1))
  fi
  # The census runs whether or not the target met its bar: a red target is exactly
  # when the classification is worth reading.
  python3 "$CENSUS" --tree "$t" || true
  if [ "$BASELINE" -eq 1 ]; then
    python3 "$CENSUS" --tree "$t" --baseline || true
  fi
done

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo " $FAILURES of $(echo "$WANT" | wc -w | tr -d ' ') target(s) failed"
exit "$FAILURES"
