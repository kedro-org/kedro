Feature: Jupyter targets in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"

  Scenario: Execute jupyter setup target
    When I execute the kedro command "jupyter setup"
    Then I should get a message including "The kernel has been created successfully at"

  Scenario: Execute jupyter notebook target
    When I execute the kedro jupyter command "notebook --no-browser"
    Then I wait for the jupyter webserver to run for up to "120" seconds
    Then jupyter notebook should run on port 8888

  Scenario: Execute jupyter lab target
    When I execute the kedro jupyter command "lab --no-browser"
    Then I wait for the jupyter webserver to run for up to "120" seconds
    Then Jupyter Lab should run on port 8888
