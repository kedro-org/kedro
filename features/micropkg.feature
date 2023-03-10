Feature: Micro-package target in new project

  Background:
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have installed the project dependencies

  @fresh_venv
  Scenario: Package a micro-package
    When I execute the kedro command "micropkg package pipelines.data_science"
    Then I should get a successful exit code
    And I should get a message including "'project_dummy.pipelines.data_science' packaged!"

  @fresh_venv
  Scenario: Package a micro-package from manifest
    Given I have micro-packaging settings in pyproject.toml
    When I execute the kedro command "micropkg package --all"
    Then I should get a successful exit code
    And I should get a message including "Packaged 'pipelines.data_science' micro-package!"
