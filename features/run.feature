Feature: Run Project


  Scenario: Run default python entry point with example code

    Local environment should be used by default when no env option is specified.

    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    When I execute the kedro command "run"
    Then I should get a successful exit code
    And the logs should show that 4 nodes were run

  Scenario: Run parallel runner with default python entry point with example code
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    When I execute the kedro command "run --runner=ParallelRunner"
    Then I should get a successful exit code
    And the logs should show that "split_data" was run
    And the logs should show that "train_model" was run
    And the logs should show that "predict" was run
    And the logs should show that "report_accuracy" was run

  Scenario: Run default python entry point without example code
    Given I have prepared a config file without starter
    And I have run a non-interactive kedro new without starter
    When I execute the kedro command "run"
    Then I should get an error exit code
    And I should get an error message including "Pipeline contains no nodes"

  Scenario: Run kedro run with config file
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have prepared a run_config file with config options
    When I execute the kedro command "run --config run_config.yml"
    Then I should get a successful exit code
    And the logs should show that 1 nodes were run

  Scenario: Run kedro run with config from archive and OmegaConfigLoader
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have set the OmegaConfigLoader in settings
    When I execute the kedro command "package"
    Then I should get a successful exit code
    When I execute the kedro command "run --conf-source dist/conf-project_dummy.tar.gz"
    Then I should get a successful exit code
    And the logs should show that 4 nodes were run

  Scenario: Run kedro run with config file and override option
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    And I have prepared a run_config file with config options
    When I execute the kedro command "run --config run_config.yml --pipeline __default__"
    Then I should get a successful exit code
    And the logs should show that 4 nodes were run

  Scenario: Run kedro run with extra parameters
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter "default"
    When I execute the kedro command "run --params extra1=1,extra2=value2"
    Then I should get a successful exit code
    And the logs should show that 4 nodes were run
