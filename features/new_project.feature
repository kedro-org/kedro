Feature: New Kedro project

  Scenario: Create a new kedro project without example code
    Given I have prepared a config file
    When I run a non-interactive kedro new without starter
    Then the expected project directories and files should be created
    And the pipeline should contain no nodes

  Scenario: Create a new kedro project with example code
    Given I have prepared a config file
    When I run a non-interactive kedro new with starter
    Then the expected project directories and files should be created
    And the pipeline should contain nodes

  Scenario: Plugins are installed and Create a new kedro project with custom plugin starter
    Given I have installed the test plugin
    When I run a non-interactive kedro new with custom plugin starter
    Then I should get a successful exit code
    Then the expected project directories and files should be created
    And the pipeline should contain nodes
