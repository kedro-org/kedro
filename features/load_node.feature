Feature: load_node in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"

  Scenario: Execute ipython load_node magic
    When I install project and its dev dependencies
    And I execute the load_node magic command
    Then the logs should show that load_node executed successfully
