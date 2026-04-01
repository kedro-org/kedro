Feature: Project Inspection API

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"

  Scenario: get_project_snapshot returns a valid snapshot for a default project
    When I call get_project_snapshot on the project
    Then the snapshot is a valid ProjectSnapshot

  Scenario: The snapshot captures correct project metadata
    When I call get_project_snapshot on the project
    Then the snapshot metadata project_name is "project-dummy"
    And the snapshot metadata package_name is "project_dummy"

  Scenario: The snapshot captures registered pipelines
    When I call get_project_snapshot on the project
    Then the snapshot pipelines include "__default__", "data_engineering", "data_science", "data_processing"

  Scenario: The snapshot captures catalog datasets
    When I call get_project_snapshot on the project
    Then the snapshot datasets include "example_iris_data", "example_model", "example_predictions"

  Scenario: The snapshot captures parameter keys
    When I call get_project_snapshot on the project
    Then the snapshot parameters include "example_learning_rate", "example_num_train_iter", "example_test_data_ratio"
