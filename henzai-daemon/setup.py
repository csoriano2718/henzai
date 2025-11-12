from setuptools import setup, find_packages

setup(
    name="henzai",
    version="0.1.0",
    description="AI-First GNOME Desktop Assistant",
    author="Christian Soriano",
    packages=find_packages(),
    install_requires=[
        "dasbus>=1.7",
        "PyGObject>=3.42.0",
    ],
    entry_points={
        "console_scripts": [
            "henzai-daemon=henzai.main:main",
        ],
    },
    python_requires=">=3.12",
)










