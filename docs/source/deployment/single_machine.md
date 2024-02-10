# Single-machine deployment
This topic explains how to deploy Kedro on a production server. You can use three alternative methods to deploy your Kedro pipelines:

- [Container-based deployment](#container-based)
- [Package-based deployment](#package-based)
- [CLI-based deployment](#cli-based)


## Container-based
This approach uses containers, such as [`Docker`](https://www.docker.com/) or any other container solution, to build an image and run the entire Kedro project in your preferred environment.

For the purpose of this walk-through, we are going to assume a Docker workflow. We recommend the [Kedro-Docker plugin](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-docker) to streamline the process, and [usage instructions are in the plugin's README.md](https://github.com/kedro-org/kedro-plugins/blob/main/README.md). After you’ve built the Docker image for your project locally, transfer the image to the production server. You can do this as follows:

### How to use container registry
A container registry allows you to store and share container images. [Docker Hub](https://www.docker.com/products/docker-hub) is one example of a container registry you can use for deploying your Kedro project. If you have a [Docker ID](https://docs.docker.com/docker-id) you can use it to push and pull your images from the Docker server using the following steps.

Tag your image on your local machine:

```console
docker tag <image-name> <DockerID>/<image-name>
```

Push the image to Docker hub:

```console
docker push <DockerID>/<image-name>
```

Pull the image from Docker hub onto your production server:

```console
docker pull <DockerID>/<image-name>
```

```{note}
Repositories on Docker Hub are set to public visibility by default. You can change your project to private on the Docker Hub website.
```

The procedure for using other container registries, like AWS ECR or GitLab Container Registry, will be almost identical to the steps described above. However, authentication will be different for each solution.

## Package-based
If you prefer not to use containerisation, you can instead package your Kedro project using [`kedro package`](../development/commands_reference.md#deploy-the-project).

Run the following in your project’s root directory:

```console
kedro package
```

Kedro builds the package into the `dist/` folder of your project, and creates a `.whl` file, which is [a Python packaging format for binary distribution](https://packaging.python.org/overview/).

The resulting `.whl` package only contains the Python source code of your Kedro pipeline, not any of the `conf/` and `data/` subfolders nor the `pyproject.toml` file.
The project configuration is packaged separately in a `tar.gz` file. This compressed version of the config files excludes any files inside your `local` directory.
This means that you can distribute the project to run elsewhere, such as on a separate computer with different configuration, data and logging. When distributed, the packaged project must be run from within a directory that contains the `pyproject.toml` file and `conf/` subfolder (and `data/` if your pipeline loads/saves local data). This means that you will have to create these directories on the remote servers manually.

Recipients of the `.whl` file need to have Python and `pip` set up on their machines, but do not need to have Kedro installed. The project is installed to the root of a folder with the relevant `conf/` and `data/` subfolders, by navigating to the root and calling:

```console
pip install <path-to-wheel-file>
```

After having installed your project on the remote server, run the Kedro project as follows from the root of the project:

```console
python -m project_name
```

## CLI-based
If neither containers nor packages are viable options for your project, you can also run it on a production server by cloning your project codebase to the server using the [Kedro CLI](../development/commands_reference.md).

You will need to follow these steps to get your project running:

### Use GitHub workflow to copy your project
This workflow posits that development of the Kedro project is done on a local environment under version control by Git. Commits are pushed to a remote server (e.g. GitHub, GitLab, Bitbucket, etc.).

Deployment of the (latest) code on a production server is accomplished through cloning and the periodic pulling of changes from the Git remote. The pipeline is then executed on the server.

Install Git on the server, how to do this depends on the type of server you're using. You can verify if the installation was successful by running:

```console
git --version
```

Setup git (optionally)

```console
git config --global user.name "Server"
git config --global user.email "server@server.com"
```

[Generate a new SSH key for the server](https://docs.github.com/en/github/authenticating-to-github/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) and [add this new key to your GitHub account](https://docs.github.com/en/github/authenticating-to-github/adding-a-new-ssh-key-to-your-github-account).

Finally clone the project to the server:

```console
git clone <repository>
```

### Install and run the Kedro project
Once you have copied your Kedro project to the server, you need to follow these steps to install all project requirements and run the project.

Install Kedro on the server using pip:

```console
pip install kedro
```

or using conda:

```console
conda install -c conda-forge kedro
```

Install the project’s dependencies, by running the following in the project's root directory:

```console
pip install -r requirements.txt
```

After having installed your project on the remote server you can run the Kedro project as follows from the root of the project:

```console
kedro run
```

You can also integrate the above steps in a bash script and run it in the relevant directory.
