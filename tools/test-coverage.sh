#!/bin/bash

set -e
set -u
set -o pipefail

print_start_time() {
    echo ""; echo "--- Started at $(date +"%d-%m-%Y %T")"; echo ""
}

print_finish_time() {
    echo ""; echo "--- Finished at $(date +"%d-%m-%Y %T")"; echo ""
}

get_git_branch() {
    echo $(git rev-parse --abbrev-ref HEAD)
}

TEST_REPORT_FILE="."
delete_the_old_test_report() {
    TEST_REPORTS_FOLDER=".test-run-reports"
    mkdir -p "${TEST_REPORTS_FOLDER}"
    TEST_REPORT_FILE="${TEST_REPORTS_FOLDER}/test-report-$(get_git_branch).html"
    rm -f ${TEST_REPORT_FILE} && echo "Deleting old test report file: ${TEST_REPORT_FILE}"
}

COVERAGE_REPORT_FOLDER=".coverage-reports"
COVERAGE_REPORT_FILE=""
delete_the_old_coverage_report_folder_and_create_a_new_one() {
    mkdir -p "${COVERAGE_REPORT_FOLDER}"
    COVERAGE_REPORT_FOLDER="${COVERAGE_REPORT_FOLDER}/coverage-report-$(get_git_branch)"
    rm -fr ${COVERAGE_REPORT_FOLDER} && echo "Deleting old test coverage folder: ${COVERAGE_REPORT_FOLDER}"
    COVERAGE_REPORT_FILE="${COVERAGE_REPORT_FOLDER}/index.html"
}

test_run_exit_code=0
SOURCES_FOLDER=kedro
TESTS_FOLDER=tests
TARGET_TEST_FOLDERS="$@"
TARGET_TEST_FOLDERS="${TARGET_TEST_FOLDERS:-"${TESTS_FOLDER}/"}"
run_test_runner() {
    echo ""; echo "~~~ Running tests with coverage on branch '$(get_git_branch)'"
    set -x
    pytest --cov-config default_coverage_report.toml     \
           --cov-report html:${COVERAGE_REPORT_FOLDER}   \
           --cov=${SOURCES_FOLDER} ${TARGET_TEST_FOLDERS} \
           --html="${TEST_REPORT_FILE}"                  \
           || test_run_exit_code="$?" && true
    set +x
    echo ""; echo "~~~ The test report file created: ${TEST_REPORT_FILE}";
    echo ""; echo "~~~ The test coverage report can be found by opening: ${COVERAGE_REPORT_FILE}"

    echo ""
    if [[ ${test_run_exit_code} -eq 0 ]]; then
       echo "SUCCESSFUL: all tests have successfully PASSED."
    else
       echo "FAILURE: one or more tests have FAILED or another reason for failure returned by 'pytest'."
    fi
    echo ""; echo "Exiting with error code '${test_run_exit_code}'."
}

print_start_time
delete_the_old_test_report
delete_the_old_coverage_report_folder_and_create_a_new_one
run_test_runner
print_finish_time

exit ${test_run_exit_code}
