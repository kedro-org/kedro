Feature: Run kedro info

    Scenario: Plugins are installed and detected by kedro info
        Given I have installed the test plugin
        When I execute the kedro command "info"
        Then I should get a successful exit code
        And I should get a message including "plugin: 0.1"
