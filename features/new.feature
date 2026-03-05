Feature: New Kedro project

  Scenario: Create a new kedro project without example code
    Given I have prepared a config file without starter
    When I run a non-interactive kedro new without starter
    Then the expected project directories and files should be created

  Scenario: Create a new kedro project with example code
    Given I have prepared a config file
    When I run a non-interactive kedro new with starter "default"
    Then the expected project directories and files should be created

  Scenario: Plugins are installed and create a new kedro project with custom plugin starter
    Given I have prepared a config file
    Given I have installed the test plugin
    When I run a non-interactive kedro new with starter "test_plugin_starter"
    Then the expected project directories and files should be created
