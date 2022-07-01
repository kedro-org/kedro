Feature: List Kedro Starters

  Scenario: List all starters with custom starters from plugin
    Given I have prepared a config file
    And I have installed the test plugin
    And I have run a non-interactive kedro new with starter "default"
    When I execute the kedro command "starter list"
    Then I should get a successful exit code
    And I should get a message including "test_plugin_starter"
