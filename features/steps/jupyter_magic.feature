Feature: Jupyter targets in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "spaceflights-pandas"

  Scenario: Execute jupyter load_node magic
    When I execute the magic command "load_node"
    Then the notebook should show "split_data_node is not found"
