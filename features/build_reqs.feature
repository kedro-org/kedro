Feature: build-reqs target in new project

  @fresh_venv
  Scenario: Execute build-reqs target
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter
    And I have updated kedro requirements
    And I have executed the kedro command "build-reqs"
    When I add scrapy>=1.7.3 to the requirements
    And I execute the kedro command "build-reqs"
    Then I should get a successful exit code
    And requirements should be generated
    And scrapy should be in the requirements
