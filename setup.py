import os
from setuptools import setup
from os.path import expanduser

setup(
    name = "libhpc_deployer",
    version = "0.3",
    package_dir={'':'src/main'},
    packages=['deployer','deployer.config','deployer.config.platform',
              'deployer.config.software','deployer.core','deployer.plugins'],
    package_data={'':['*.yaml']},
    dependency_links=['git+https://github.com/jcohen02/saga-python#egg=saga-python',
                      'git+https://github.com/saga-project/radical.utils#egg=radical.utils'],
    install_requires=['saga-python','radical.utils','apache-libcloud==0.14.0','PyYAML'],
    # Console scripts to be generated
    entry_points={
        'console_scripts': [
            'libhpc-run-job = deployer.libhpc_run_job:libhpc_run_job',
        ],
    },
    
    # Package PyPI metadata
    author = "Jeremy Cohen",
    author_email = "jeremy.cohen@imperial.ac.uk",
    license = "BSD 3-Clause",
    description = ("A library and command-line tool for running HPC "
                   "applications on clusters and clouds. Currently focuses "
                   "on supporting the Nektar++ spectral/hp element "
                   "framework (http://www.nektar.info/)"),
    long_description=("The Libhpc Deployer library supports deployment of HPC "
                      "jobs to a variety of platforms. At present there is "
                      "support for PBS, OpenStack and Amazon EC2 platforms. "
                      "Users of the library are required to prepare metadata "
                      "describing their target platform(s) and details of "
                      "any software to be deployed to the target resources. "
                      "This metadata and the job specification describing the "
                      "job to be undertaken are provided in YAML format."),
    keywords = "libhpc deployer cloud cluster",
    url = "https://github.com/london-escience/libhpc-deployer",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)