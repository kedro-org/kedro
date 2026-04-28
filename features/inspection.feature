Feature: Project Inspection API

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"

  Scenario: A developer inspects a project to understand its structure without running it
    When I call get_project_snapshot on the project
    Then the snapshot pipelines include "__default__", "data_engineering", "data_science", "data_processing"
    And the snapshot datasets include "example_iris_data", "example_model", "example_predictions"
    And the snapshot parameters include "example_learning_rate", "example_num_train_iter", "example_test_data_ratio"
