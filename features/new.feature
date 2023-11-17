
Feature: Kedro Add-ons E2E Testing
  As a Kedro developer
  I want to have end-to-end tests for the add-ons flow
  So that I can ensure the 'kedro new' command works correctly with various add-ons combinations

  Scenario Outline: Create a new Kedro project without any add-ons
    Given the user runs the command "kedro new --addons=none"
    When the user completes the project setup without any add-ons
    Then a new Kedro project is created without any add-ons
    And "kedro run" executes successfully on the newly created project

  Scenario Outline: Create a new Kedro project with all add-ons except 'viz' and 'pyspark'
    Given the user runs the command "kedro new --addons=lint,docs,data,logging"
    When the user completes the project setup with specified add-ons
    Then a new Kedro project is created with all add-ons except 'viz' and 'pyspark'
    And "kedro run" executes successfully on the newly created project

  Scenario Outline: Create a new Kedro project with all add-ons
    Given the user runs the command "kedro new --addons=all"
    When the user completes the project setup with all add-ons
    Then a new Kedro project is created with all add-ons
    And "kedro run" executes successfully on the newly created project

  Scenario Outline: Create a new Kedro project with only 'pyspark' add-on
    Given the user runs the command "kedro new --addons=pyspark"
    When the user completes the project setup with 'pyspark' add-on
    Then a new Kedro project is created with only 'pyspark' add-on
    And "kedro run" executes successfully on the newly created project

  Scenario Outline: Create a new Kedro project with only 'viz' add-on
    Given the user runs the command "kedro new --addons=viz"
    When the user completes the project setup with 'viz' add-on
    Then a new Kedro project is created with only 'viz' add-on
    And "kedro run" executes successfully on the newly created project
