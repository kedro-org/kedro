# Node Grouping in Kedro: Pipelines, Tags, and Namespaces

When deploying a **Kedro** project, grouping nodes effectively is crucial for **maintainability, debugging, and execution control**. This document provides an overview of three key grouping methods: **Pipelines, Tags, and Namespaces**, along with a list of their strengths, limitations, best use cases, and links to how to use them.

# Choosing Between Pipelines, Tags, and Namespaces in Kedro

## Nodes grouping using Pipelines in Kedro

### What Works
- If your project contains multiple pipelines, you can use them as predefined node groupings for deployment.
- Pipelines can be executed separately in the deployment environment.
- With the visualisation in Kedro Viz, you can switch to see different pipeline in a more isolated view
![Switching between different pipelines in Kedro Viz](../meta/images/kedro_viz_switching_pipeline.gif)

### What Doesn't Work
- If you need to create custom node groupings that are different with your existing pipelines, creating new pipelines for them may not be convenient. Instead, you can use alternative grouping methods such as tags or namespaces.
- You cannot execute multiple pipelines in a single step because the kedro run --pipeline command allows running only one pipeline at a time.
- You can switch between different pipelines in Kedro Viz, but the visualization does not support collapsing or expanding pipelines within Kedro Viz.

### Best Used When
- Your project is structured in a way that requires executing pipelines separately in the deployment environment.

### Not to Use When
- You need to run multiple pipelines together.
- You want to use the expand or collapse functionality in Kedro Viz

### How to Implement
- Run using:
  ```bash
  kedro run --pipeline=<your_pipeline_name>
  ```
- More information: [Run a pipeline by name](https://docs.kedro.org/en/stable/nodes_and_pipelines/run_a_pipeline.html#run-a-pipeline-by-name)

---

## Tags

### What Works
- You can tag individual nodes or the entire pipeline, allowing flexible execution of specific sections without modifying the pipeline structure.
- Kedro-Viz provides a clear visualization of tagged nodes, making it easier to understand.
- ![Filters Panel in Kedro Viz](../meta/images/kedro_viz_filters_tags.png)

### What Doesn't Work
- Nodes with the same tag can exist in different pipelines, making debugging and maintaining the codebase more challenging.
- Executing multiple tags in a single step isn't always possible, and sometimes it's not guarentee to run if a part of pipeline is not populated before at the time of execution.

### Best Used When
- You need to run specific nodes that don’t belong to the same pipeline.
- You want to rerun only a subset of nodes in a large pipeline.

### Not to Use When
- The tagged nodes have strong dependencies, which might cause execution failures.
- Tags are not hierarchical, so tracking groups of nodes can become difficult.
- Tags do not enforce structure like pipelines or namespaces.

### How to Implement
- Run using:
  ```bash
  kedro run --tags=<your_tag_name>
  ```
- More information: [How to tag a node](https://docs.kedro.org/en/stable/nodes_and_pipelines/nodes.html#how-to-tag-a-node)

---

## Namespaces

### What Works
- Namespaces allow you to group nodes, ensuring clear dependencies and separation within a pipeline while maintaining a consistent structure.
- Similar to pipelines or tags, you can enable selective execution using namespaces.
- Namespaces improve visualization in Kedro-Viz.
![Switching expanding namespaced pipeline in Kedro Viz](../meta/images/kedro_viz_expanding_namespace.gif)



### What Doesn't Work
- You cannot run multiple namespaces simultaneously—Kedro only allows executing one namespace at a time.
- **Defining namespace at Node-level:** If you define namespaces at the node level, they behave similarly to tags and do not guarantee execution consistency.
- **Defining namespace at Pipeline-level:** When applying a namespace at the pipeline level, Kedro automatically renames all inputs, outputs, and parameters within that pipeline. This can introduce naming conflicts.

### Best Used When
- You want to organize nodes logically within a pipeline while keeping a structured execution flow.
- Your pipeline structure is well-defined, and using namespaces improves visualization in Kedro-Viz.
- Customizing deployment groups by adding namespaces at the node level.

### Not to Use When
- Your pipeline has only a few nodes—adefining namespaces at the node level behaves like tags without ensuring execution consistency, while defining them at the pipeline level helps with modularization by renaming inputs, outputs, and parameters but can introduce naming conflicts if the pipeline is connected elsewhere or parameters are referenced outside the pipeline.dding namespaces may introduce unnecessary complexity.
- Applying namespaces at the pipeline level makes management harder due to automatic renaming of inputs/outputs.

### How to Implement
- Run using:
  ```bash
  kedro run --namespace=<your_namespace_name>
  ```
- More information: [Namespaces](https://docs.kedro.org/en/stable/nodes_and_pipelines/namespaces.html)

---

## Summary Table

| Aspect | Pipelines | Tags | Namespaces |
|--------|-----------|------|-----------|
| **What Works** | If you're happy with how the nodes are structured in your existing pipeline, or your pipeline is low complexity and a new grouping view is not required then you don't have to use any alternatives | Tagging individual nodes or the entire pipeline allows flexible execution of specific sections without altering the pipeline structure, and Kedro-Viz offers clear visualization of these tagged nodes for better understanding. | Namespaces group nodes to ensure clear dependencies and separation within a pipeline, allow selective execution, and can be visualized using Kedro-Viz. |
| **What Doesn't Work** | "If you need to create custom node groupings that don’t align with your existing pipelines, creating new pipelines for them may not be convenient. Instead, you can use alternative grouping methods such as tags or namespaces. | Lack of hierarchical structure, making debugging and maintaining the codebase more challenging, and executing multiple tags in a single step isn't always possible if parts of the pipeline aren't populated beforehand. | Defining namespaces at the node level behaves like tags without ensuring execution consistency, while defining them at the pipeline level helps with modularization by renaming inputs, outputs, and parameters but can introduce naming conflicts if the pipeline is connected elsewhere or parameters are referenced outside the pipeline. |
| **Syntax** | `kedro run --pipeline=<your_pipeline_name>` | `kedro run --tags=<your_tag_name>` | `kedro run --namespace=<your_namespace_name>` |
