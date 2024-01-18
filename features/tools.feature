Feature: New Kedro project with tools

  Scenario: Create a new Kedro project without any tools
    Given I have prepared a config file with tools "none"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "none"

  Scenario: Create a new Kedro project with all tools except 'viz' and 'pyspark'
    Given I have prepared a config file with tools "1,2,3,4,5"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "1,2,3,4,5"
    