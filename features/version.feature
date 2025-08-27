Feature: Kedro version

  @fresh_venv
  Scenario: Check kedro version
    When I ask the CLI for a version
    Then CLI should print the version in an expected format

  @fresh_venv
  Scenario: Check kedro version using python -m
    When I ask the CLI for a version using python -m
    Then CLI should print the version in an expected format
