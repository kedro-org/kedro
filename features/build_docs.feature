Feature: build-docs target in new project

  @fresh_venv
  Scenario: Execute build-docs target
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter
    And I have updated kedro requirements
    And I have executed the kedro command "install"
    When I execute the kedro command "build-docs"
    Then I should get a successful exit code
    And docs should be generated
