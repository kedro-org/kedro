Feature: New Kedro project with tools

  Scenario: Create a new Kedro project without any tools
    Given I have prepared a config file with tools "none"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "none"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with all tools except 'viz' and 'pyspark'
    Given I have prepared a config file with tools "lint, test, log, docs, data"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "lint, test, log, docs, data"
    Then I should get a successful exit code
