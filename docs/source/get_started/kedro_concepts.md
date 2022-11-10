# Kedro concepts

<!-- TO DO -- add a bit more info here and design some graphics -->

It is time to introduce the most basic elements of Kedro. 

## Node

In Kedro, a node is a wrapper for a Python function that names the inputs and outputs of that function. Nodes are the building block of a pipeline, and the output of one node can be the input of another.

## Pipeline

A pipeline organises the dependencies and execution order of a collection of nodes, and connects inputs and outputs while keeping your code modular. The pipeline determines the **node execution order** by resolving dependencies and does *not* necessarily run the nodes in the order in which they are passed in.

## Data Catalog

The Kedro Data Catalog is the registry of all data sources that the project can use that manages loading and saving of data. It maps the names of node inputs and outputs as keys in a `DataSet`, which is a Kedro class that can be specialised for different types of data storage. 

Kedro provides a [number of different built-in datasets](/kedro.extras.datasets) for different file types and file systems so you don’t have to write the logic for reading/writing data.

## Kedro project directory structure

Kedro projects follow a default structure that uses specific folders to store datasets, notebooks, configuration and source code. We advise you to retain the structure to make it easy to share your projects with other Kedro users, but you can adapt the folder structure if you need to.

You'll learn more about the details of the Kedro project structure in the next section when you create [your first Kedro project](new_project.md).