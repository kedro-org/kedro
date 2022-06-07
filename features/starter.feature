Feature: List Kedro Starters

  Scenario: List all starters with custom starters from plugin
    Given I have installed the test plugin
    When I execute the kedro command "starter list"
    Then I should get a successful exit code
    And I should get a message including "test_plugin_starter"
