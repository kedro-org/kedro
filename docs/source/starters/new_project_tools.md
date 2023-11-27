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

Including the Documentation tool adds a `docs` directory to your project structure and includes the Sphinx setup files, allowing for the auto generation of HTML documentation. 
The aim of this tool reflects Kedro's commitment to best practices in understanding code and facilitating collaboration. It will help you to create and maintain guides and API docs.
See the [official documentation](https://docs.kedro.org/en/stable/tutorial/package_a_project.html#add-documentation-to-a-kedro-project) for guidance on adding documentation to a Kedro project.

### Data Structure 

The Data Structure tool provides a standardised folder hierarchy for your project data, which includes predefined folders such as raw, intermediate, and processed data.
This tool is fundamental if you want to include example pipelines during the creation of your project as it can not be omitted from the tool selections.
This tool will help you in maintaining a clean and organised data workflow, with clear separation of data at various processing stages.
We believe a well-organised data structure is key to efficient data management, allowing for scalable and maintainable data pipelines.
You can learn more about Kedro's recommended [project directory structure](https://docs.kedro.org/en/stable/get_started/kedro_concepts.html#kedro-project-directory-structure).

### PySpark 

The PySpark tool modifies the project's `requirements.txt` to include PySpark dependencies and adjusts the project setup for Spark jobs, this will allow you to process datasets using Apache Spark for scalable data processing.
PySpark aligns with Kedro's scalability principle, as it provides data processing capabilities for large datasets.
See the [PySpark integration documentation](https://docs.kedro.org/en/stable/integrations/pyspark_integration.html) for more information on setup and usage.

### Kedro Viz

This tool will add visualisation to your project by including Kedro-Viz, which creates an interactive web-app to visualise your pipelines allowing for an intuitive understanding of data on your DAG.
See the [Kedro-Viz documentation](https://docs.kedro.org/projects/kedro-viz/en/stable/index.html) for more information on using this tool.


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

---
Here's a flowchart to guide your choice of tools and examples:
```{mermaid}
:alt: mermaid-Decision making diagram for setting up a new Kedro project

flowchart TD
    A[Start] -->|Run 'kedro new'| B{Select Tools}
    B -->|None| C{Include example pipeline?}
    B -->|All| C{Include example pipeline?}
    B -->|Combination of Lint, Test, Logs, Docs, Data, PySpark, Viz| C
    C -->|No| D[Proceed without example pipeline and only the basic template]
    C -->|Yes| E{Which add-ons are included?}
    E -->|None| F[Include 'spaceflights-pandas' example]
    E -->|All| I[Include 'spaceflights-pyspark-viz' example]
    E -->|Viz without PySpark| G[Include 'spaceflights-pandas-viz' example]
    E -->|PySpark without Viz| H[Include 'spaceflights-pyspark' example]
    E -->|Viz & PySpark| I[Include 'spaceflights-pyspark-viz' example]
    E -->|Without Viz and PySpark| F[Include 'spaceflights-pandas' example]
    D --> J[Project setup complete]
    F --> J
    G --> J
    H --> J
    I --> J

```

