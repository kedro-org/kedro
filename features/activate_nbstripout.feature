Feature: Activate_nbstripout target in new project

  Scenario: Check nbstripout git post commit hook functionality
    Given I have prepared a config file
    And I have run a non-interactive kedro new with starter
    And I have added a test jupyter notebook
    And I have initialized a git repository
    And I have added the project directory to staging
    And I have committed changes to git
    And I have executed the kedro command "activate-nbstripout"
    When I execute the test jupyter notebook and save changes
    And I add the project directory to staging
    And I commit changes to git
    And I remove the notebooks directory
    And I perform a hard git reset to restore the project to last commit
    Then there should be an additional cell in the jupyter notebook
    And the output should be empty in all the cells in the jupyter notebook
