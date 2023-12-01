Feature: New Kedro project with tools

  Scenario: Create a new Kedro project without any tools
    Given I have prepared a config file with tools "none"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "none"
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with all tools except 'viz' and 'pyspark'
    Given I have prepared a config file with tools "1,2,3,4,5"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "1,2,3,4,5"
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with all tools
    Given I have prepared a config file with tools "all"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "all"
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with only 'pyspark' tool
    Given I have prepared a config file with tools "6"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "6"
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with only 'viz' tool
    Given I have prepared a config file with tools "7"
    When I run a non-interactive kedro new without starter
    Then the expected tool directories and files should be created with "7"
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code
