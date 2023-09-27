# Share a project's Kedro-Viz

```{note}
Kedro-Viz sharing was introduced in version 7.0.0.
```

This page describes how to deploy the Kedro-Viz for your project so you can share it with others. It uses the [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) as an example.

If you haven't installed Kedro [follow the documentation to get set up](../get_started/install.md). In your terminal window, navigate to the folder you want to store the project.

If you have not yet worked through the tutorial, use the [Kedro starter for spaceflights](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights) to generate the project with working code in place. Type the following in your terminal:

```bash
kedro new --starter=spaceflights
```

When prompted for a project name, you can enter anything, but we will assume `Spaceflights` throughout.

When your project is ready, navigate to the root directory of the project.

## Update and install the dependencies

Kedro-Viz requires specific minimum versions of `fsspec` and `kedro` to deploy your project.

You can ensure you have these correct versions by updating the `requirements.txt` file in the `src` folder of the Kedro project to the following:

```text
fsspec>=2023.9.0
kedro>=0.18.2
```

Install the dependencies from the project root directory by typing the following in your terminal:

```bash
pip install -r src/requirements.txt
```

## Configure your AWS S3 bucket and set credentials

You can host your project's Kedro-Viz as a deployed URL on Amazon S3. You must first create an S3 bucket and then enable static website hosting. To do so, follow the [AWS tutorial](https://docs.aws.amazon.com/AmazonS3/latest/userguide/HostingWebsiteOnS3Setup.html) to configure a static website on Amazon S3.

Once that's completed, you'll need to set your AWS credentials as environment variables in your terminal window, as shown below:

```bash
export AWS_ACCESS_KEY_ID="your_access_key_id"
export AWS_SECRET_ACCESS_KEY="your_secret_access_key"
```

For more information, see the official AWS documentation about [how to work with credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html).

## Deploy the project

You're now ready to deploy your Kedro-Viz project. Start Kedro-Viz by running the following command in your terminal:

```bash
kedro viz
```

Click the **Deploy and share** icon in the lower-left of the application. You will see a modal dialog to select your relevant AWS Bucket Region and enter your Bucket Name.

Once those two details are complete, click **Deploy**. A hosted, shareable URL will be returned to you after the deploy completes.

Here's an example of the flow:

![](../meta/images/kedro-viz-deploy.gif)

## Permissions and access control

All permissions and access control are controlled by AWS. It's up to you, the user, if you want to allow anyone to see your project or limit access only to certain IP addresses, users, or groups.

You can control who can view your visualisation using [bucket and user policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-iam-policies.html) or [access control lists](https://docs.aws.amazon.com/AmazonS3/latest/userguide/acls.html). See the official AWS documentation for more information.
