#!/bin/bash

PROG="$(basename $0)"
TEST_DIR="test"
COVERAGE=

has_program() {
  [ -n "$(whereis $1 | cut -d: -f2-)" ]
}

find_python_coverage() {
  local python_coverage=
  for python_coverage in coverage coverage2; do
    if has_program "${python_coverage}"; then
      COVERAGE="${python_coverage}"
      return
    fi
  done
  echo "${PROG}: Could not find python-coverage tool"
  exit 1
}

die() {
  echo "${PROG}: $1"
  exit 1
}

find_python_coverage

export PYTHONPATH="$(pwd)"

pushd "${TEST_DIR}"

rm -f .coverage
echo "Run tests under Python 2 (and generates test coverage report)"
${COVERAGE} run suite_all.py || die "Tests failed"

echo "Run tests under Python 3"
python3 suite_all.py || die "Tests failed"

echo "Run tests with Clang's binding"
python suite_clang_cindex.py || die "Tests failed"

echo "Output test coverage report"
${COVERAGE} report -m

popd

if [ -z "${CLANG_SOURCE}" ]; then
  echo -n "CLANG_SOURCE="
  read CLANG_SOURCE
fi

if [ -z "${CLANG_INCLUDE}" ]; then
  echo -n "CLANG_INCLUDE="
  read CLANG_INCLUDE
fi

OUTPUT1="$(mktemp --suffix=.py)"
OUTPUT2="$(mktemp --suffix=.py)"

echo "Generate cindex.py to ${OUTPUT1} with Python 2"
time python2 bin/cbind \
  -o "${OUTPUT1}" \
  -i "${CLANG_SOURCE}/include/clang-c/Index.h" \
  -l libclang.so \
  --config demo/cindex.yaml \
  -- -I "${CLANG_INCLUDE}"

echo "Generate cindex.py to ${OUTPUT2} with Python 3"
time python3 bin/cbind \
  -o "${OUTPUT2}" \
  -i "${CLANG_SOURCE}/include/clang-c/Index.h" \
  -l libclang.so \
  --config demo/cindex.yaml \
  -- -I "${CLANG_INCLUDE}"

diff "${OUTPUT1}" "${OUTPUT2}"

rm -f "${OUTPUT1}"
rm -f "${OUTPUT2}"
