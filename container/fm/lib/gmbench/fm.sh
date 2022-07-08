#!/bin/bash
#
# Author: Stefan Haller <stefan.haller@iwr.uni-heidelberg.de>
#
# This script template expects the following variables to be set:
# - METHOD (string)
# - PARAMETERS (bash array).
#
set -eu -o pipefail

if [[ $# -lt 3 ]]; then
	echo "$0 DATASET INSTANCE_IDX TRIAL" >&1
	exit 64
fi

dataset="$1"
instance="$2"
trial="$3"

input="datasets/${dataset}/${dataset}${instance}.dd.xz"
output_dir="benchmark/${trial}/${METHOD}/${dataset}/${dataset}${instance}"
mkdir -p "$(dirname "${output_dir}")"

output_temp_dir=$(umask 0077 && mktemp -d)
trap 'rm -rf "${output_temp_dir}"' EXIT

if [[ ! -d "${output_dir}" ]]; then
	timeout -k 60 -s INT 500 qap_dd "${PARAMETERS[@]}" \
		--seed 42 \
		--output "${output_temp_dir}/output.txt" \
		"${input}" \
		>"${output_temp_dir}/stdout.txt" \
		2>"${output_temp_dir}/stderr.txt" || true

	(cd "${output_temp_dir}" && gzip *.txt)

	mv -T "${output_temp_dir}" "${output_dir}"
fi
