
Feature: Kedro Add-ons E2E Testing

  Scenario: Create a new Kedro project without any add-ons
    When I run the command "kedro new --addons=none"
    And I complete the project setup without any add-ons
    Then a new Kedro project should be created without any add-ons
    And "kedro run" should execute successfully on the newly created project

  Scenario: Create a new Kedro project with all add-ons except 'viz' and 'pyspark'
    When I run the command "kedro new --addons=lint,docs,data,logging"
    And I complete the project setup with specified add-ons
    Then a new Kedro project should be created with all add-ons except 'viz' and 'pyspark'
    And "kedro run" should execute successfully on the newly created project

  Scenario: Create a new Kedro project with all add-ons
    When I run the command "kedro new --addons=all"
    And I complete the project setup with all add-ons
    Then a new Kedro project should be created with all add-ons
    And "kedro run" should execute successfully on the newly created project

  Scenario: Create a new Kedro project with only 'pyspark' add-on
    When I run the command "kedro new --addons=pyspark"
    And I complete the project setup with 'pyspark' add-on
    Then a new Kedro project should be created with only 'pyspark' add-on
    And "kedro run" should execute successfully on the newly created project

  Scenario: Create a new Kedro project with only 'viz' add-on
    When I run the command "kedro new --addons=viz"
    And I complete the project setup with 'viz' add-on
    Then a new Kedro project should be created with only 'viz' add-on
    And "kedro run" should execute successfully on the newly created project
