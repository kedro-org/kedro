Feature: Jupyter targets in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter

  Scenario: Execute jupyter-notebook target
    When I execute the kedro jupyter command "notebook --no-browser"
    Then jupyter notebook should run on port 8888

  Scenario: Execute jupyter-lab target
    When I execute the kedro jupyter command "lab --no-browser"
    Then Jupyter Lab should run on port 8888

  Scenario: Execute node convert into Python files
    Given I have added a test jupyter notebook
    When I execute the test jupyter notebook and save changes
    And I execute the kedro jupyter command "convert --all"
    And Wait until the process is finished
    Then I should get a successful exit code
    And Code cell with node tag should be converted into kedro node
