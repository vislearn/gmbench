#!/bin/bash
#
# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>
#
# This script template expects the following variables to be set:
# - METHOD (string)
# - REQUIRES_BIJECTIVE (0 or 1)
# - REQUIRES_NONPOSITIVE (0 or 1)
# - REQUIRES_ZERO_UNARIES (0 or 1)
# - MATLAB_INCLUDES (bash array).
#
set -eu -o pipefail

if [[ $# -lt 3 ]]; then
	echo "$0 DATASET INSTANCE_IDX TRIAL" >&1
	exit 64
fi

suffix=
[[ "${REQUIRES_BIJECTIVE}"    -eq 1 ]] && suffix="${suffix}b"
[[ "${REQUIRES_NONPOSITIVE}"  -eq 1 ]] && suffix="${suffix}n"
[[ "${REQUIRES_ZERO_UNARIES}" -eq 1 ]] && suffix="${suffix}z"
[[ -n "${suffix}" ]] && suffix="_${suffix}"

dataset="$1"
instance="$2"
trial="$3"

input="datasets_matlab/${dataset}/${dataset}${instance}${suffix}.mat"
output_dir="benchmark/${trial}/${METHOD}/${dataset}/${dataset}${instance}"
mkdir -p "$(dirname "${output_dir}")"

batch=()
batch+=("addpath('/usr/local/lib/matlab/wrapper')")
for include in "${MATLAB_INCLUDES[@]}"; do
	batch+=("addpath(genpath('/usr/local/lib/matlab/${include}'))")
done
batch+=("wrapper_${METHOD}('${input}')")

if [[ -v MATLAB_LICENSE_SERVER ]]; then
	export MLM_LICENSE_FILE="${MATLAB_LICENSE_SERVER}"
fi

output_temp_dir=$(umask 0077 && mktemp -d)
trap 'rm -rf "${output_temp_dir}"' EXIT

if [[ ! -d "${output_dir}" ]]; then
	timeout -k 60 -s INT 500 matlab \
		-batch "$(printf '%s; ' "${batch[@]}")" \
		>"${output_temp_dir}/stdout.txt" \
		2>"${output_temp_dir}/stderr.txt" || true

	(cd "${output_temp_dir}" && gzip *.txt)

	mv -T "${output_temp_dir}" "${output_dir}"
fi
