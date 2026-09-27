#!/bin/bash
# tkbuild.sh TOKE_DIR "SRC [SRC...]" OUT [extra toke flags...] : compile+link toke file(s)
# (dependency order; several files become one binary). Uses bin/clang to work around
# toke's 8192-byte stdlib source-list buffer truncating on long checkout paths.
TD="$(cd "$1" && pwd)"; SRCS="$2"; OUTB="$3"; shift 3
HERE="$(cd "$(dirname "$0")" && pwd)"
IMPORTS=$(cat $SRCS | grep -oE 'i=[a-z0-9_]+:std\.[a-z0-9_]+' | sed 's/.*std\.//' | sort -u | tr '\n' ' ')
rm -f "$OUTB"
W2_TOKE_DIR="$TD" W2_IMPORTS="$IMPORTS" PATH="$HERE/bin:$PATH" "$TD/toke" "$@" $SRCS --out "$OUTB"
