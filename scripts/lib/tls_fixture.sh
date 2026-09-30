#!/bin/sh
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# tls_fixture.sh <dir> — throwaway certificates for testing https verification. (F5.11)
#
# Writes, into <dir>, freshly generated and never reused:
#   ca.pem  ca.key      a certificate authority that nothing on this machine trusts. A test
#                       trusts it by pointing SSL_CERT_FILE at ca.pem, for one process only.
#   good.pem good.key   signed by that CA, for IP 127.0.0.1: what a trusted server looks like.
#   other.pem other.key signed by that CA, for DNS other.invalid only: a trusted chain that
#                       names another host (the host-name check).
#   self.pem self.key   self-signed, for IP 127.0.0.1: an untrusted chain for the right
#                       address (the chain check).
#   done                written last, so a caller polling for it never reads half a set.
#
# The keys are 2048-bit RSA and the certificates last one day. Nothing here is a secret:
# the CA exists for the length of one test and is trusted by nothing else. .invalid is
# reserved (RFC 6761) and never resolves, so other.pem can name no real host.
set -eu
DIR="$1"
mkdir -p "$DIR"
cd "$DIR"
OPENSSL="${OPENSSL:-openssl}"
q() { "$@" >/dev/null 2>&1; }

q "$OPENSSL" req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=loke test CA" \
  -keyout ca.key -out ca.pem \
  -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign"

leaf() {
  # $1 = name, $2 = subjectAltName
  q "$OPENSSL" req -newkey rsa:2048 -nodes -subj "/CN=$1" -keyout "$1.key" -out "$1.csr"
  printf 'basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=%s\n' "$2" > "$1.ext"
  q "$OPENSSL" x509 -req -in "$1.csr" -CA ca.pem -CAkey ca.key -CAcreateserial -days 1 \
    -extfile "$1.ext" -out "$1.pem"
  rm -f "$1.csr" "$1.ext"
}
leaf good "IP:127.0.0.1"
leaf other "DNS:other.invalid"

q "$OPENSSL" req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=127.0.0.1" \
  -keyout self.key -out self.pem -addext "subjectAltName=IP:127.0.0.1"

echo ok > done
