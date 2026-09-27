#!/bin/sh
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# check_https_dispatch.sh — F5.11: the ONE measurement the automated tests cannot make.
#
# tests/integration/test_hosted_requests.tk shows, against a loopback recorder over plain
# http, that the Anthropic and OpenAI dispatch now arrives with its method, path, body and
# headers. Whether the same call reaches a provider over HTTPS (TLS handshake, SNI,
# certificate, the provider accepting the request as sent) needs a real key and costs money,
# so nothing in the gate does it. This script does it once, when YOU run it with your key.
#
#   LOKE_HTTPS_CHECK_KEY=sk-ant-... scripts/check_https_dispatch.sh
#
# What it sends: one request to https://api.anthropic.com/v1/messages through
# core.providers.transport.post, the call every hosted dispatch uses, with the production
# endpoint, headers and body builder, parsed by core.providers.anthropic. The fixed synthetic
# prompt "Reply with the word OK." and max_tokens 1. No user data, no settings, no keychain.
# The model is claude-haiku-4-5 unless LOKE_HTTPS_CHECK_MODEL names another. The cost is a
# handful of tokens.
#
# It prints PASS with the model the reply named, or FAIL with the reason loke recorded. It
# needs a build (scripts/build_loke.sh) and TOKE_DIR, as scripts/run_tests.sh does.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# DISABLED until toke T-58 is fixed. toke's https client verifies no certificate, so this
# script would hand your key to anyone able to intercept the connection, and
# core.providers.transport now refuses every non-loopback send anyway. Re-enable only when a
# test shows an untrusted certificate being rejected.
echo "check_https_dispatch: disabled — toke's https client does not verify certificates (T-58), so no key is sent. Nothing was sent." >&2
exit 3
if [ -z "${LOKE_HTTPS_CHECK_KEY:-}" ]; then
  echo "check_https_dispatch: set LOKE_HTTPS_CHECK_KEY to your Anthropic key. Nothing was sent." >&2
  exit 2
fi
MODEL="${LOKE_HTTPS_CHECK_MODEL:-claude-haiku-4-5}"
WORK=$(mktemp -d /tmp/loke-https-check.XXXXXX)
trap 'rm -rf "$WORK"' EXIT INT TERM

# Written here, never in the tree, so run_tests.sh can never discover it and spend money.
cat > "$WORK/test_https_dispatch.tk" <<EOF
(* Copyright 2026 loke contributors
   SPDX-License-Identifier: Apache-2.0 *)

m=test.manual.httpsdispatch;

i=io:std.io;
i=str:std.str;
i=env:std.env;
i=ant:core.providers.anthropic;
i=pt:core.providers.types;
i=tr:core.providers.transport;

f=main():i64{
  let key=mt env.get("LOKE_HTTPS_CHECK_KEY") {
    \$ok:v v;
    \$err:e ""
  };
  let req=\$completionrequest{
    modelid:"$MODEL";
    messages:@(pt.usermsg("Reply with the word OK."));
    systemprompt:"";
    maxtokens:1 as u32;
    temperature:0.0;
    stream:false
  };
  let raw=tr.post(tr.anthropicurl();pt.anthropicbody(req);tr.anthropicheaders(key));
  if(str.len(raw)==0){
    io.println("check_https_dispatch: FAIL, nothing came back: no connection, no TLS, or no response");
    <1
  }el{};
  let n=mut.str.len(raw);
  if(n>400){ n=400 }el{};
  io.println("check_https_dispatch: the provider answered: \(str.slice(raw;0;n))");
  let r:\$completionresponse=ant.parseplain(raw);
  if(pt.iscompletion(r)){
    io.println("check_https_dispatch: PASS, https://api.anthropic.com answered; model \(r.modelid), tokens in \(r.inputtokens as i64), out \(r.outputtokens as i64)");
    <0
  }el{
    io.println("check_https_dispatch: FAIL, \(pt.completionerror(r))");
    <1
  }
};
EOF

cd "$ROOT" && BUILDDIR="${BUILDDIR:-/tmp/loke-https-check-build}" LOKE_HTTPS_CHECK_KEY="$LOKE_HTTPS_CHECK_KEY" \
  scripts/run_tests.sh "$WORK"
