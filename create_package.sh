#!/usr/bin/env bash
ARCHIVE='slack-jira-comments.zip'
TMP_DIR="lambda_zip_contents"

# Setup clean package env
rm -f ${ARCHIVE}
mkdir ${TMP_DIR}

# Copy our own code
cp -r src/* "${TMP_DIR}/"

# Get the location of the packages
python_lib=$(python -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")

for line in $(cat requirements.txt | cut -d= -f1); do
    source="${python_lib}/${line}"
    if [[ ! -d ${source} ]]; then
        source="${source}.py"
    fi
    cp -r "${source}" "${TMP_DIR}/"
done

cd ${TMP_DIR} && zip --quiet --recurse-paths ../${ARCHIVE} * && cd - >/dev/null

rm -rf ${TMP_DIR}