# Using tools to configure your Kedro project

<!--TO DO-->
<!--Detailed usage of add-ons goes here-->

## Kedro tools <!--Section needs better name--> 

Tools are [modular functionalities that can be added to a basic Kedro project] . They allow for [...]. When creating a new project, you may select one or more of the available tools, or none at all.

The available tools include: linting, testing, custom logging, documentation, data structure, Pyspark, and Kedro-Viz.

### Linting 

<!--
    - What the tool modifies in the project requirements
    - Does it have any prerequisites/couplings/exclusions with other tools?
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    see: https://docs.kedro.org/en/stable/development/linting.html#install-the-tools
-->

### Testing 

<!--
    - What the tool modifies in the project structure and requirements
    - Does it have any prerequisites/couplings/exclusions with other tools?
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    - For more info look at testing [documentaion](https://docs.kedro.org/en/stable/development/automated_testing.html#set-up-automated-testing-with-pytest)
-->

### Custom logging 

<!--
    - What the tool modifies in the project structure
    - Does it have any prerequisites/couplings/exclusions with other tools?
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    see: https://docs.kedro.org/en/stable/logging/index.html
-->

### Documentation 

<!--
    - What the tool modifies in the project structure and requirements
    - Does it have any prerequisites/couplings/exclusions with other tools?
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    - For more information look at our [docs docs](https://docs.kedro.org/en/stable/tutorial/package_a_project.html#add-documentation-to-a-kedro-project)
-->

### Data Structure 

<!--
    - What the tool modifies in the project structure
    - Does it have any prerequisites/couplings/exclusions with other tools? NOTE: examples cannot omit data structure
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    see: https://docs.kedro.org/en/stable/get_started/kedro_concepts.html#kedro-project-directory-structure
-->

### Pyspark 

<!--
    - What the tool modifies in the project structure and requirements
    - Does it have any prerequisites/couplings/exclusions with other tools?
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    see: https://docs.kedro.org/en/stable/integrations/pyspark_integration.html
-->

### Kedro Viz

<!--
    - What the tool modifies in the project structure and requirements
    - Does it have any prerequisites/couplings/exclusions with other tools?
    - What does it enable/how to utilise the tool in the new project setup
    - Tools link back to Kedro principles; why do we recommend using this tool, what value does it provide to the user/link on best practice (short, 1-2 sentence)
    - For more information visit our [Kedro-Viz documentation](https://docs.kedro.org/projects/kedro-viz/en/stable/index.html)
-->


## Configuring your tool selection
<!--Should this section come before or after the listing out of the tools?-->

There are several ways to configure these tools when creating a new Kedro project.

### Through the `kedro new` prompt
<!--
Walkthrough of using it intentionally
Be sure to note restrictions of the syntax
Be sure to note default values
-->

### Through the use of the flag `kedro new --tools/-t=...`
<!--
Walkthrough of using it intentionally
Be sure to note restrictions of the syntax
Be sure to note default values if applicable
-->

### Using a configuration file `kedro new --config/-c=`
<!--
Walkthrough of using it intentionally
Be sure to note restrictions of the syntax
Be sure to note default values
Be sure to note what happens when using a config file that omits add-ons - project fails
-->


