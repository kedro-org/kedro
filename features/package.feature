Feature: Package target in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter
    And I have executed the kedro command "install --no-build-reqs"

  @fresh_venv
  Scenario: Install package
    When I execute the kedro command "package"
    Then I should get a successful exit code
    When I install the project's python package
    And I execute the installed project package
    Then I should get a successful exit code

  @fresh_venv
  Scenario: Install package after running kedro build-reqs
   Given I have updated kedro requirements
   When I execute the kedro command "build-reqs"
   Then I should get a successful exit code
   When I execute the kedro command "package"
   Then I should get a successful exit code
   When I install the project's python package
   And I execute the installed project package
   Then I should get a successful exit code
