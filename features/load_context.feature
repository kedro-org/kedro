Feature: Custom Kedro project
    Background:
        Given I have prepared a config file
        And I have run a non-interactive kedro new with starter "default"

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

    Scenario: Hooks from installed plugins are automatically registered and work with the default runner
        Given I have installed the test plugin
        When I execute the kedro command "run"
        Then I should get a successful exit code
        And I should get a message including "Reached after_catalog_created hook"
        # The below line has been changed to DEBUG level. Currently, it's not possible to show
        # this message anymore because it's logged before `session._setup_logging` is called.
        # It is yet to be determined if we should keep it this way, so leaving this here until
        # we have more clarity on the necessity of these logging messages.
        # And I should get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"

    Scenario: Hooks from installed plugins are automatically registered and work with the parallel runner
        Given I have installed the test plugin
        When I execute the kedro command "run --runner=ParallelRunner"
        Then I should get a successful exit code
        And I should get a message including "Reached after_catalog_created hook"
        # See explanation in test above.
        # And I should get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"

    Scenario: Disable automatically registered plugin hooks
        Given I have installed the test plugin
        And I have disabled hooks for "test-plugin" plugin via config
        When I execute the kedro command "run"
        Then I should get a successful exit code
        And I should not get a message including "Registered hooks from 1 installed plugin(s): test-plugin-0.1"
        And I should not get a message including "Reached after_catalog_created hook"
        # See explanation in test above.
        # And I should get a message including "Hooks are disabled for plugin(s): test-plugin-0.1"
