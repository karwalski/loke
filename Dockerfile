# Dockerfile — reproducible build and measurement environment for loke.
#
# Exists so that a measurement can be reproduced by somebody else. Every
# benchmark result records this image's digest (see benchmarks/lib/result.py),
# so a number can always be traced back to the environment that produced it.
#
# The toolchain commits are NOT specified here. They are read from
# TOOLCHAIN.lock at build time, so the lock file stays the single source of
# truth and this file cannot drift away from it.
#
#   docker build -t loke-bench .
#   docker run --rm -v "$PWD/benchmarks/results:/loke/benchmarks/results" loke-bench
#
# Note: this image targets linux/amd64 by default. Results measured here are
# NOT comparable with results measured on Apple Silicon, and anything
# concerning local inference performance must say which it was — see epic LC1
# on what a non-Apple-Silicon environment cannot validate.

FROM debian:bookworm-20250630-slim

ENV DEBIAN_FRONTEND=noninteractive \
    TOKE_DIR=/opt/toke \
    OOKE_DIR=/opt/ooke \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Build toolchain for toke/ooke (C + clang for LLVM IR), plus the libraries
# loke links against, plus Python for the measurement harnesses.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      clang \
      git \
      ca-certificates \
      libssl-dev \
      libsqlite3-dev \
      zlib1g-dev \
      python3 \
      python3-venv \
      make \
      curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /loke

# Copy the lock first so the toolchain layer caches independently of source.
COPY TOOLCHAIN.lock ./

# Clone and check out exactly what TOOLCHAIN.lock pins. A moving HEAD here
# would make every result in this image unreproducible.
RUN set -eu; \
    lockval() { sed -n "s/^$1[[:space:]]*=[[:space:]]*//p" TOOLCHAIN.lock | head -1; }; \
    git clone "$(lockval toke_repo)" "$TOKE_DIR"; \
    git -C "$TOKE_DIR" checkout --detach "$(lockval toke_commit)"; \
    git clone "$(lockval ooke_repo)" "$OOKE_DIR"; \
    git -C "$OOKE_DIR" checkout --detach "$(lockval ooke_commit)"; \
    echo "toke $(lockval toke_commit) / ooke $(lockval ooke_commit)" > /opt/toolchain-pin.txt

RUN make -C "$TOKE_DIR"
RUN make -C "$OOKE_DIR" all

COPY . .

# Fail the image build if the checked-out toolchain disagrees with the lock.
RUN chmod +x scripts/*.sh && ./scripts/check_toolchain.sh

# The build is expected to fail while the toolchain migration is on hold, so
# it is not run here. Re-enable once epic F10 completes:
#   RUN ./scripts/build_loke.sh

CMD ["python3", "-m", "benchmarks.run", "--help"]
