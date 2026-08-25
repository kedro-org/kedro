Feature: Dataset validation in a project

  Scenario: Run a pipeline whose dataset passes its declared validator
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have added a "passing" validator to the example dataset
    When I execute the kedro command "run"
    Then I should get a successful exit code
    And the logs should show that 4 nodes were run

  Scenario: A failing validator blocks the run at the dataset boundary
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have added a "failing" validator to the example dataset
    When I execute the kedro command "run"
    Then I should get an error exit code
    And I should get an error message including "Validation failed for dataset 'example_iris_data' on load"

  Scenario: The project setting switches validation off
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have added a "failing" validator to the example dataset
    And I have disabled dataset validation in the project settings
    When I execute the kedro command "run"
    Then I should get a successful exit code
    And the logs should show that 4 nodes were run

  Scenario: Validators work with the parallel runner
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have added a "passing" validator to the example dataset
    When I execute the kedro command "run --runner=ParallelRunner"
    Then I should get a successful exit code
    And the logs should show that "split_data" was run
