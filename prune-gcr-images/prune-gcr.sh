#!/bin/bash

# Copyright © 2017 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


function print_help {
   cat <<EOF
   Use: prune-gcr.sh [--debug --help]
   Options:
   -r, --repository The full gcr.io path to the docker image, e.g.,
                    gcr.io/uwit-mci-iam/app-name

   -d, --before-date  A date in the format of 'YYYY-MM-DD'

   -x, --dry-run      Run the script but don't actually delete anything

   -m, --min-images   The minimum number of images to preserve in the repository.
                      Even if images are older than the --before-date argument,
                      they will be preserved if there are no others available.

   -h, --help      Show this message and exit
   -g, --debug     Show commands as they are executing
EOF
}

min_images=10

function parse_args {
  while (( $# ))
  do
    case $1 in
      --repository|-r)
        shift
        repository="$1"
        ;;
      --before-date|-d)
        shift
        before_date="$1"
        ;;
      --min-images|-m)
        shift
        min_images="$1"
        ;;
      --dry-run|-x)
        dry_run=1
        ;;
      --help|-h)
        print_help
        exit 0
        ;;
      --debug|-g)
        DEBUG=1
        ;;
      *)
        echo "Invalid Option: $1"
        print_help
        exit 1
        ;;
    esac
    shift
  done

  test -z "${DEBUG}" || set -x
  export DEBUG="${DEBUG}"
  if [[ -z "${repository}" ]]
  then
    >&2 echo "No --repository/-r supplied."
    >&2 echo "Run with --help for more information."
    return 1
  fi
  if [[ -z "${before_date}" ]]
  then
    >&2 echo "No --before-date/-d supplied."
    >&2 echo "Run with --help for more information."
    return 1
  fi
}


get_total_image_count() {
  # Only count unique digests to make sure we don't accidentally
  # delete references to digests we intend to keep.
  gcloud container images list-tags ${repository} -q --limit=99999 \
   | tail -n +2 \
   | cut -f1 -d' ' | uniq \
   | wc -l | sed 's| ||g'
}


get_list_of_digests(){
  gcloud container images list-tags ${repository} -q --limit=99999 \
    --sort-by=TIMESTAMP \
    --filter="timestamp.datetime < '${before_date}'" \
  | tail -n +2 | cut -f1 -d' ' | uniq
}

main(){
  local C=0
  output="$(get_list_of_digests)"
  local total_count=$(get_total_image_count)
  local max_deletions=$(( ${total_count} - ${min_images} ))
  if [[ "${max_deletions}" -le "0" ]]
  then
    max_deletions=0
  fi
  for digest in ${output}
  do
    if [[ "${C}" -ge "${max_deletions}" ]]
    then
      >&2 echo "Maximum number of digest deletions (${max_deletions}) reached. "
      return 0
    fi
    target_image="${repository}@sha256:${digest}"
    command="gcloud container images delete -q --force-delete-tags ${target_image}"
    if [[ -z "${dry_run}" ]]
    then
      (
        set -x
        $command
        set +x
      )
    else
      echo "[NOT RUNNING] ${command}"
    fi
    let C=C+1
  done
  local output_prefix='Deleted'
  test -z "${dry_run}" || output_prefix="[DID NOT] ${output_prefix}"
  >&2 echo "${output_prefix} ${C} images in ${repository}"
}

parse_args "$@" || exit $?
if [[ -n "${dry_run}" ]]
then
  >&2 echo "[DRY RUN] No images will actually be deleted!"
fi
main || exit $?
