from glob import glob

from setuptools import setup

template_files = []
for pattern in ["**/*", "**/.*", "**/.*/**", "**/.*/.**"]:
    template_files.extend(
        [
            name.replace("kedro/", "", 1)
            for name in glob("kedro/templates/" + pattern, recursive=True)
        ]
    )

setup(
    package_data={
        "kedro": ["py.typed"] + template_files
    },
)
