# Next steps: Tutorial

In this tutorial, we construct nodes and pipelines for a price-prediction model to illustrate the steps of a typical Kedro workflow.

The tutorial takes approximately **30 minutes** to complete. You will work in the terminal and by inspecting project files in an IDE or text editor. There is no Jupyter notebook for the project.

*It is 2160, and the space tourism industry is booming. Globally, thousands of space shuttle companies take tourists to the Moon and back. You have been able to source data that lists the amenities offered in each space shuttle, customer reviews, and company information.*

***Project***: *You want to construct a model that predicts the price for each trip to the Moon and the corresponding return flight.*

## Tutorial steps

- [Tutorial Template](tutorial_template.md)
- [Set Up Data](../tutorials/set_up_data.md)
- [Create a Pipeline](../tutorials/create_a_pipeline.md)
- [Add Another Pipeline](../tutorials/add_another_pipeline.md)
- [Test a Project](../tutorials/test_a_project.md)
- [Package a Project](../deploy/package_a_project.md)
- [Spaceflights Tutorial FAQs](spaceflights_tutorial_faqs.md)

![](../meta/images/moon-rocket.png)

Photo by <a href="https://unsplash.com/@ivvndiaz">Ivan Diaz</a> on <a href="https://unsplash.com/s/photos/spaceship">Unsplash</a>

## Watch the video

<iframe width="100%" height="315" src="https://www.youtube.com/embed/YBY2Lcz7Gw4" frameborder="0" allowfullscreen></iframe>

## Get help

If you encounter an issue with the tutorial:

- Check the [spaceflights tutorial FAQ](spaceflights_tutorial_faqs.md) to see if we have answered the question already.
- Use [Kedro-Viz](https://docs.kedro.org/projects/kedro-viz/en/latest/) to visualise your project and better understand how the datasets, nodes, and pipelines fit together.
- Use the [#questions channel](https://slack.kedro.org/) on our Slack channel to ask the community for help.
- Search the [searchable archive of Slack discussions](https://linen-slack.kedro.org/).

## Terminology

We explain any Kedro-specific terminology as we introduce it, and further information can be found in the [glossary](../getting-started/glossary.md). Some additional terminology may not be familiar to some readers, such as the concepts below.

### Project root directory

Also known as the "root directory," this is the parent folder for the entire project. It is the top-level folder that contains all other files and directories associated with the project.

### Dependencies

These are Python packages or libraries that an individual project depends upon to complete a task. For example, the Spaceflights tutorial project depends on the [scikit-learn](https://scikit-learn.org/stable/) library.

### Standard development workflow

When you build a Kedro project, you will typically follow a standard development workflow:

1. **Set up the project template**
    - Create a new project and install project dependencies.
    - Configure credentials and any other sensitive/personal content, and logging.

2. **Set up the data**
    - Add data to the `data` folder.
    - Reference all datasets for the project.

3. **Create the pipeline**
    - Construct nodes to make up the pipeline.
    - Choose how to run the pipeline: sequentially or in parallel.

4. **Package the project**
    - Build the project documentation.
    - Package the project for distribution.
