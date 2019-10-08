#!/bin/bash
#
# Build only spec files changed since the last git commit.
#
# Takes no arguments.
#
# Outputs the full path of built files, for paste-into-browser convenience.
#
# How it works:
# - Determines files changed since last commit
# - Filters to only specs (specs/*/*/*.rst)
# - Maps those by release subdir (second part of the path)
# - Builds all the changed specs in each release subdir
#
# Why it's fast:
# Not, as you may think, because we're only building the specific spec files.
# It is actually because we're restricting sphinx-build to only looking at the
# specific subdirectory/ies of those changed files. Even if only building a
# subset of files, sphinx-build normally parses all of them anyway (probably
# for index-building purposes). Since you're normally building (one spec in)
# the latest release's directory, this saves sphinx-build parsing the 600-ish
# specs from previous releases.

# Temp file storing the full path to built specs
tmpf=/tmp/specs.$$
function cleanup {
  rm -f $tmpf
}
trap cleanup EXIT

# Map, keyed by release dir name, of spec files thereunder
declare -A specs_by_release
# Look for specs changed since last commit
for f in $(git diff --name-only HEAD~1 | grep -E 'specs/[^/]+/[^/]+/[^/]+\.rst'); do
  # echo $f | cut -d/ -f2, but faster
  release=${f#*/}
  release=${release%%/*}
  # doc/source/... has symlinks, and is where sphinx-build expects sources
  specs_by_release[$release]=${specs_by_release[$release]}" doc/source/$f"
done

if [[ ${#specs_by_release[@]} -eq 0 ]]; then
  echo "No spec files changed, nothing to build."
  exit 0
fi

# Build all changed specs per release directory
for release in "${!specs_by_release[@]}"; do
  src=doc/source/specs/$release
  bld=doc/build/html/specs/$release
  files=${specs_by_release[$release]}
  echo "fast-specs: Building for ${release}:$files"
  sphinx-build -c doc/source $src $bld $files
  # Save the full path to built files. (Wait until the end to output these, so
  # they're not lost between subdirectories.)
  for f in $files; do
    p=$(echo $f | sed 's,/source/,/build/html/,; s/rst$/html/')
    realpath $p >> $tmpf
  done
done

echo "================"
echo "fast-specs built:"
cat $tmpf

exit 0
