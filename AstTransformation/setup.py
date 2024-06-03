from setuptools import setup, find_packages

setup(
    name="ast_transform",
    version="0.1.1-alpha",
    packages=find_packages(),
    install_requires=[
        "black==24.4.2",
        "cffi==1.16.0",
        "click==8.1.7",
        "colorama==0.4.6",
        "gevent==24.2.1",
        "greenlet==3.0.3",
        "mypy-extensions==1.0.0",
        "packaging==23.1",
        "pathspec==0.12.1",
        "platformdirs==4.2.1",
        "protobuf==5.26.1",
        "pycparser==2.22",
        "pytz==2024.1",
        "setuptools==69.5.1",
        "tomli==2.0.1",
        "typing_extensions==4.11.0",
        "websocket==0.2.1",
        "websocket-client==1.8.0",
        "websockets==12.0",
        "zope.event==5.0",
        "zope.interface==6.4"
    ],
    include_package_data=True,
    description="Query planner using Python language for LLM calls to APIs written in any programming language",
    url="https://github.com/goodw21985/ApiConductor",
    author="Bob Goodwin",
    author_email="goodw21985@live.com",
    license="Proprietary",  # Indicate that the package is proprietary
)
