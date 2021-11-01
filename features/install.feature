Feature: install target in new project
  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter
    And I have updated kedro requirements
    Then src/requirements.in must not exist

  @fresh_venv
  Scenario: Execute install target
    When I execute the kedro command "install"
    Then I should get a successful exit code
    And src/requirements.in file must exist

  @fresh_venv
  Scenario: Execute install target without compiled requirements
    When I execute the kedro command "install --no-build-reqs"
    Then I should get a successful exit code
    And src/requirements.in must not exist
