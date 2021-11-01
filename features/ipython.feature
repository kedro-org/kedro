Feature: IPython target in new project

  Scenario: Execute ipython target
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter
    When I execute the kedro command "ipython"
    Then I should get a message including "An enhanced Interactive Python"
    And I should get a message including "INFO - ** Kedro project project-dummy"
    And I should get a message including "INFO - Defined global variable `context`, `session`, `catalog` and `pipelines`"
