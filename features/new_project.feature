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
