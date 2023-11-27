Feature: New Kedro project with add-ons

  Scenario: Create a new Kedro project without any add-ons
    Given I have prepared a config file with add-ons "none"
    When I run a non-interactive kedro new without starter
    Then the expected add-on directories and files should be created

  Scenario: Create a new Kedro project with all add-ons except 'viz' and 'pyspark'
    Given I have prepared a config file with add-ons "1,2,3,4,5"
    When I run a non-interactive kedro new without starter
    Then the expected add-on directories and files should be created
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with all add-ons
    Given I have prepared a config file with add-ons "all"
    When I run a non-interactive kedro new without starter
    Then the expected add-on directories and files should be created
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with only 'pyspark' add-on
    Given I have prepared a config file with add-ons "6"
    When I run a non-interactive kedro new without starter
    Then the expected add-on directories and files should be created
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code

  Scenario: Create a new Kedro project with only 'viz' add-on
    Given I have prepared a config file with add-ons "7"
    When I run a non-interactive kedro new without starter
    Then the expected add-on directories and files should be created
    Given I have installed the project dependencies
    When I execute the kedro command "run"
    Then I should get a successful exit code
