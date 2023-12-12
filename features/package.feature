Feature: Package target in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have installed the project dependencies

  @fresh_venv
  Scenario: Install package
    When I execute the kedro command "package"
    Then I should get a successful exit code
    When I install the project's python package
    And I execute the installed project package
    Then I should get a successful exit code
