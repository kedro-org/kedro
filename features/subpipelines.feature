Feature: Run subpipelines

  Note that node tagging below is currently hardcoded in `pipeline_template.py`

  Background:
    Given I have included a pipeline definition in a project template
    And I have defined a node "node_1" tagged with "apple", "orange", "banana", "lemon", "grape", "coconut", "fresh strawberries!"
    And I have defined a node "node_2" tagged with "apple", "orange", "lemon"
    And I have defined a node "node_3" tagged with "apple", "orange", "banana", "cherry"
    And I have defined a node "node_4" tagged with "apple", "cherry"
    And I have set the project log level to "DEBUG"

  Scenario: Run subpipeline of one node using two tags

    When with tags "coconut", "grape", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 1 nodes were run
    And the console log should show that "node_1" was run

  Scenario: Run subpipeline of one node using a tag with spaces and special characters

    When with tags "fresh strawberries!", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 1 nodes were run
    And the console log should show that "node_1" was run

  Scenario: Run subpipeline of two nodes using one tag

    When with tags "lemon", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 2 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run

  Scenario: Run subpipeline of three nodes using one tag

    When with tags "orange", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 3 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run
    And the console log should show that "node_3" was run

  Scenario: Run subpipeline of four nodes using one tag

    When with tags "apple", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 4 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run
    And the console log should show that "node_3" was run
    And the console log should show that "node_4" was run

  Scenario: Run subpipeline of four nodes using two tags with discrete ranges

    Effectively checks a valid subpipeline is constructed when a tag is issued
    which applies to a subset of nodes, and another tag is issued which applies
    to the other subset of nodes.

    When with tags "lemon", "apple", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 4 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run
    And the console log should show that "node_3" was run
    And the console log should show that "node_4" was run

  Scenario: Run subpipeline with conflicting tags

    Run pipeline with one tag that is tagged to 2 nodes and another that is
    tagged to 4 nodes

    When with tags "lemon", "cherry", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 4 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run
    And the console log should show that "node_3" was run
    And the console log should show that "node_4" was run

  Scenario: Run an incomplete subpipeline (missing node)

    When with tags "coconut", "cherry", I execute the kedro command "run"
    Then I should get an error exit code

  Scenario: Run subpipeline using invalid tag

    When with tags "blob", I execute the kedro command "run"
    Then I should get an error exit code

  Scenario: Run subpipeline using a valid and invalid tag

    When with tags "blob", "lemon", I execute the kedro command "run"
    Then I should get a successful exit code
    And the console log should show that 2 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run

  Scenario: Run subpipeline using a subset of nodes as starting point

    When I execute the kedro command "run --from-nodes node_1"
    Then I should get a successful exit code
    And the console log should show that 4 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run
    And the console log should show that "node_3" was run
    And the console log should show that "node_4" was run

  Scenario: Run subpipeline using a subset of nodes as end point

    When I execute the kedro command "run --to-nodes node_2"
    Then I should get a successful exit code
    And the console log should show that 2 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run

  Scenario: Run subpipeline using a range of nodes

    When I execute the kedro command "run --from-nodes node_1 --to-nodes node_3"
    Then I should get a successful exit code
    And the console log should show that 3 nodes were run
    And the console log should show that "node_1" was run
    And the console log should show that "node_2" was run
    And the console log should show that "node_3" was run
