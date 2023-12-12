Feature: Run kedro info
    Background:
        Given I have prepared a config file
        And I have run a non-interactive kedro new with starter "default"

    Scenario: Plugins are installed and detected by kedro info
        Given I have installed the test plugin
        When I execute the kedro command "info"
        Then I should get a successful exit code
        And I should get a message including "plugin: 0.1"
