Feature: New Kedro project with add-ons

  Scenario: Create a new Kedro project without any add-ons
    Given I have prepared a config file with add-ons "none"
    When I run a non-interactive kedro new without starter
    Then the expected project directories and files should be created
    When I execute the kedro command "run"
    Then I should get a successful exit code
