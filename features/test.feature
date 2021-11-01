Feature: Test target in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter

  Scenario: Execute successful test in new project
    When I execute the kedro command "test"
    Then I should get a successful exit code

  Scenario: Execute successful lint in new project
    When I execute the kedro command "lint --check-only"
    Then I should get a successful exit code
