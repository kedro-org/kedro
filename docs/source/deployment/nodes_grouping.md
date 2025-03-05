# Node Grouping in Kedro: Pipelines, Tags, and Namespaces

When deploying a Kedro project, grouping nodes effectively is crucial for maintainability, debugging, and execution control. This document provides an overview of three key grouping methods: Pipelines, Tags, and Namespaces, along with a list of their strengths, limitations, best use cases, and links to how to use them.

# Choosing between pipelines, tags, and namespaces in Kedro

## Grouping by pipelines

- If your project contains different pipelines, you can use them as predefined node groupings for deployment.
- Pipelines can be executed separately in the deployment environment.
- With the visualisation in Kedro Viz, you can switch to see different pipeline in a more isolated view
<br>
![Switching between different pipelines in Kedro Viz](../meta/images/kedro_viz_switching_pipeline.gif)

- If you want to group nodes differently from the current pipeline structure, instead of creating a new pipeline, you can use tags or namespaces to achieve that.
- You cannot execute more than one pipeline in a single step because the `kedro run --pipeline` command allows running only one pipeline at a time.
- You can switch between different pipelines in Kedro Viz, but the flowchart view does not support collapsing or expanding pipelines.

### Best used when
- You have already separated your logic into different pipelines, and your project is structured to execute them independently in the deployment environment

### Not to use when
- You need to run more than one pipeline together.
- You want to use the expand and collapse functionality in Kedro Viz

### How to use
- Run using:
  ```bash
  kedro run --pipeline=<your_pipeline_name>
  ```
- More information: [Run a pipeline by name](https://docs.kedro.org/en/stable/nodes_and_pipelines/run_a_pipeline.html#run-a-pipeline-by-name)

---

## Grouping by tags

- You can tag individual nodes or the entire pipeline, allowing flexible execution of specific sections without modifying the pipeline structure.
- Kedro-Viz provides a clear visualisation of tagged nodes, making it easier to understand.
<br>
![Filters Panel in Kedro Viz](../meta/images/kedro_viz_filters_tags.png)

- Nodes with the same tag can exist in different pipelines, making debugging and maintaining the codebase more challenging.

### Best used when
- You need to run specific nodes that don’t belong to the same pipeline.
- You want to rerun a subset of nodes in a large pipeline.

### Not to use when
- The tagged nodes have strong dependencies, which might cause execution failures.
- Tags are not hierarchical, so tracking groups of nodes can become difficult.
- Tags do not enforce structure like pipelines or namespaces.

### How to use
- Run using:
  ```bash
  kedro run --tags=<your_tag_name>
  ```
- More information: [How to tag a node](https://docs.kedro.org/en/stable/nodes_and_pipelines/nodes.html#how-to-tag-a-node)

---

## Grouping by namespaces

- Namespaces allow you to group nodes, ensuring clear dependencies and separation within a pipeline while maintaining a consistent structure.
- As the same as pipelines or tags, you can enable selective execution using namespaces.
- Kedro Viz allows expanding and collapsing namespace pipelines in the visualization.
<br>
![Switching expanding namespaced pipeline in Kedro Viz](../meta/images/kedro_viz_expanding_namespace.gif)

- You cannot run more than one namespace simultaneously—Kedro allows executing one namespace at a time.
- **Defining namespace at Node-level:** If you define namespaces at the node level, they behave similarly to tags and do not guarantee execution consistency.
- **Defining namespace at Pipeline-level:** When applying a namespace at the pipeline level, Kedro automatically renames all inputs, outputs, and parameters within that pipeline. You will need to update your catalog accordingly.

### Best used when
- You want to organise nodes logically within a pipeline while keeping a structured execution flow. Additionally, you can nest namespace pipelines within each other.
- Your pipeline structure is well-defined, and using namespaces improves visualisation in Kedro-Viz.
- Customising deployment groups by adding namespaces at the node level.

### Not to use when
- Defining namespace at the node level behaves like tags without ensuring execution consistency, while defining them at the pipeline level helps with modularisation by renaming inputs, outputs, and parameters but can introduce naming conflicts if the pipeline is connected elsewhere or parameters are referenced outside the pipeline.dding namespaces may introduce unnecessary complexity.
- Applying namespaces at the pipeline level makes management harder due to automatic renaming of inputs/outputs.

### How to use
- Run using:
  ```bash
  kedro run --namespace=<your_namespace_name>
  ```
- More information: [Namespaces](https://docs.kedro.org/en/stable/nodes_and_pipelines/namespaces.html)

---

## Summary table

| Aspect | Pipelines | Tags | Namespaces |
|--------|-----------|------|-----------|
| **What Works** | If you're happy with how the nodes are structured in your existing pipeline, or your pipeline is low complexity and a new grouping view is not required then you don't have to use any alternatives | Tagging individual nodes or the entire pipeline allows flexible execution of specific sections without altering the pipeline structure, and Kedro-Viz offers clear visualisation of these tagged nodes for better understanding. | Namespaces group nodes to ensure clear dependencies and separation within a pipeline, allow selective execution, and can be visualised using Kedro-Viz. |
| **What Doesn't Work** | If you want to group nodes differently from the current pipeline structure, instead of creating a new pipeline, you can use alternative grouping methods such as tags or namespaces. | Lack of hierarchical structure, using tags makes debugging and maintaining the codebase more challenging | Defining namespaces at the node level behaves like tags without ensuring execution consistency, while defining them at the pipeline level helps with modularisation by renaming inputs, outputs, and parameters but can introduce naming conflicts if the pipeline is connected elsewhere or parameters are referenced outside the pipeline. |
| **Syntax** | `kedro run --pipeline=<your_pipeline_name>` | `kedro run --tags=<your_tag_name>` | `kedro run --namespace=<your_namespace_name>` |
