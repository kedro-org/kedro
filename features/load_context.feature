Feature: Custom Kedro project
    Background:
        Given I have prepared a config file
        And I have run a non-interactive kedro new with starter

    Scenario: Update the source directory to be nested
        When I move the package to "src/nested"
        And Source directory is updated to "src/nested" in pyproject.toml
        And I execute the kedro command "run"
        Then I should get a successful exit code

    Scenario: Update the source directory to be outside of src
        When I move the package to "."
        And Source directory is updated to "." in pyproject.toml
        And I execute the kedro command "run"
        Then I should get a successful exit code

    Scenario: Hooks from installed plugins are automatically registered
        Given I have installed the test plugin
        When I execute the kedro command "run"
        Then I should get a successful exit code
        And I should get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"
        And I should get a message including "Reached after_catalog_created hook"

    Scenario: Pipelines from installed plugins are added to the project's pipelines
        Given I have installed the test plugin
        When I execute the kedro command "run --pipeline from_plugin"
        Then I should get a successful exit code
        And I should get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"

    Scenario: Disable automatically registered plugin hooks
        Given I have installed the test plugin
        And I have disabled hooks for "test-plugin" plugin via config
        When I execute the kedro command "run"
        Then I should get a successful exit code
        And I should not get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"
        And I should not get a message including "Reached after_catalog_created hook"
        And I should get a message including "Hooks are disabled for plugin(s): test-plugin-0.1"
