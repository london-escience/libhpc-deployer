# Libhpc Deployer Library

The Libhpc Deployer Library is a Python library for deploying and running HPC applications on heterogeneous resources. 

This documentation provides the following information:

 - [Overview](#Overview)
 - [Installation](#Installation)
 - [Job Lifecycle](#JobLifecycle)
 - [Configuration and Metadata](#Configuration)
   - [Platform Configuration](#PlatformConfiguration)
     - [Writing a Platform Configuration](#WritingPlatformConfig)
         - [Platform Configuration - PBS_PRO Parameters](PlatformConfigPBS)
         - [Platform Configuration - SSH_FORK Parameters](PlatformConfigSSH)
         - [Platform Configuration - OPENSTACK / OPENSTACK_EC2 / EC2 Parameters](PlatformConfigOS)
         - [Platform Configuration - Additional OpenStack Parameters](PlatformConfigOSExtra)
     - [Platform Configuration Examples](#PlatformConfigExamples)
   - [Software Configuration](#SoftwareConfiguration)
     - [Writing a Software Configuration](#WritingSoftwareConfig)
     - [Software Configuration Examples](#SoftwareConfigExamples)
 - [Running a Job](#RunningAJob)
   - [Preparing a Job Specification](#JobSpecification)
   - [The libhpc\_run\_job Command-line Tool](#CommandLineTool)
- [Developer Information](#DeveloperInfo)
- [Contributors](#Contributors)
- [License](#License)
- [Acknowledgements](#Acknowledgements)

<a name="Overview"></a>
##Overview

This library provides two interfaces. For end-users a command line tool can be used to run jobs. For developers, a Python API provides access to the library's functionality to enable it to be integrated into other tools and applications.

The initial version of this library supports the following platforms:

* PBSPro
* OpenStack
* Amazon EC2

This library makes use of other standard third-party libraries that provide abstractions over a range of different hardware platforms and we therefore have the potential to support a much wider range of computational platforms in the future.

<a name="Installation"></a>
## Installation

This library currently has the following third-party dependencies (which will be automatically installed as part of the installation process described below):

 * saga-python - [http://radical-cybertools.github.io/saga-python/](http://radical-cybertools.github.io/saga-python/)
 * radical.utils - [http://radicalutils.readthedocs.org](http://radicalutils.readthedocs.org)
 * Apache Libcloud - [https://libcloud.apache.org](https://libcloud.apache.org)

_NOTE: At present, this library uses modifications to saga-python that have not yet been integrated into the main library distribution. As a result, the installer will clone saga-python from a third-party github repository containing these modifications._

To install the library, clone the github repository and then use the provided `setup.py` file to carry out the installation:

`> git clone https://github.com/london-escience/libhpc-deployer`
`> python setup.py install`

You may need to prefix the second command with `sudo` if your python packages are installed into a system directory.

######Configuration files

A configuration directory `.libhpc` will be created in your home directory. Platform and software configurations are searched for in the `.libhpc/config/platform` and `.libhpc/config/software` directories respectively, within your home directory. You can place YAML files containing platform or software configurations into these directories and they will be automatically discovered by the library.

<a name="JobLifecycle"></a>
## Job Lifecycle

The library defines a job lifecycle consisting of a set of stages. The lifecycle covers the complete process of running a job from the initial state of a collection of input data and job specification information on a user's system, thorugh running the job on a remote platform, to collection of result data back on the user's system. The heterogeneous nature of the platforms supported by the library means that not all stages in the lifecycle are required to run a job on every platform. Implementations of job deployers for different platforms can choose to provide implementations for the various stages of the job lifecycle according to their requirements. The job lifecycle stages are:

* Set platform properties
* Initialise resources
* Deploy software
* Transfer files
* Run job
* Wait for job
* Collect output
* Shutdown resources

We now provide an overview of the processes that may be carried out at each lifecycle stage:

**Set platform properties:** This stage provides the deployer with the configuration for the target platform. It is carried out when retrieving an instance of the deployer object.

**Initialise resources:** This stage handles initialisation of target resources and may involve a variety of different tasks depending on the target platform. In the case of platforms that support on-demand access to resources (e.g. Infrastructure-as-a-Service (IaaS) cloud platforms). It is used to start the required nnumber of resources for the target job and ensure that they are running and accessible.

Where a target platform needs to have other configuration carried out, such as preparing an MPI configuration or initiating a connection channel to one or more nodes, this can also be carried out in the initialisation stage. 

**Deploy software:** For platforms that do not have the required software pre-installed, this stage of the lifecycle can be used to deploy necessary software. This may, for example, be done by transferring binaries to the resource(s) or using a package repository to install the required software.

**Transfer files:** This is the stage where job confiugration/input files are transferred to remote resources in preparation for running a job. The intention is for files to be transferred securely via SFTP/SCP, using the credentials provided in the platform configuration, however other approaches may be used.

In cases where a job is to be run across multiple nodes in parallel, if a shared filesystem is not available between the nodes, it may be necessary to distribute input files to multiple nodes. This is also expected to be handled in this lifecycle stage.

**Run job:** Here the job run is initiated. Depending on the target platform, this may be carried out in different ways. For a cluster platform, a library that allows programmatic communication with the remote cluster management and job submission software (e.g. PBSPro, Grid Engine, ...) may be used. For a cloud environment, jobs may be initiated directly through an SSH connection or a helper library that communicates with the target resource(s) to initiate and manage the job.

**Wait for job completion:** This stage handles the process of waiting for a job to finish running and undertaking any tasks that need to be carried out during this period such as collecting/monitoring output information. At present, it is assumed that this output stage is synchronous and blocks until the job finishes. It is intended that an asynchronous implementation of this stage will be provided in future.

**Collect output:** Once a job has finished, the output must be retrieved or moved to some alternative permanent storage since the execution platform may not provide this. If a job has run in a parallel environment without a shared filesystem between compute nodes, it may be necessary to handle retrieval of output from multiple nodes.

**Shutdown resources:** Where a job has been run on resources that were started dynamically specifically to run the job, it is likely that the resources will need to be shut down and this is handled in this, final, stage of the lifecycle.

_More information on lifecycle stages can be found in the Developer Guide that describes how to build an adaptor for running jobs on a new target platform._

<a name="Configuration"></a>
##Configuration and Metadata

We use two different types of configuration in order to describe the software and hardware used to run jobs:

* **Platform Configuration:** Defines the details of a target computational platform.
* **Software Configuration:** Defines the details of an application to be deployed onto a computational platform.

A further type of configuration information - a _Job Specification_ - that a user writes to describe the job(s) that they want to carry out is required to run a job. More information on Job Specifications is provided in the section [Running a Job](#RunningAJob) below.

A _Platform Configuration_ is always required in order to make a target resource or platform available to run jobs. A _Software Configuration_ is only required where software needs to be installed on a target platform.

Configurations are described in YAML format. We begin by looking at _Platform Configurations_.

<a name="PlatformConfiguration"></a>
###Platform Configuration

Platform Configurations describe the configuration of a target resource so that it can be accessed and used to run jobs.

A _Platform Configuration_ is written in [YAML](http://www.yaml.org/spec/1.2/spec.html) format. This is a tree-style key-value pair format.

Platform Configurations provide a set of keys and values to describe the properties of a platform and how to access it. We now document the process of writing a platform configuration:

<a name="WritingPlatformConfig"></a>
####Writing a Platform Configuration

All platform configurations begin with the root node `platform:`

`platform` has 6 required sub-keys and a number of other optional keys that may be provided depending on the type of platform being described. 

The required platform sub-keys are:

* `type:`: The type of platform being described, currently one of the following string values:
	* `PBS_PRO`: A cluster accessed via the PBS job management system.
	* `OPENSTACK`: An OpenStack private cloud platform accessed via its native OpenStack interface. 
	* `OPENSTACK_EC2`: An OpenStack private cloud platform accesed via its EC2 interface.
	* `EC2`: The Amazon EC2 public cloud platform.
	* `SSH_FORK`: A standalone server/VM accessible via SSH.

* `id:`: A unique string identifier for the platform.
* `name:`: A string providing a descriptive name for the platform.
* `user:`: Information about the user account for running jobs - consists of a set of sub-properties that are detailed below.
* `service:`: Information about how to connect to the target platform. This will consist of different information depending on the platform. See below for more details.
* `storage:`: Information about the storage location for job data on the target platform. See below for further details.

The above properties can have different sub-properties specified depending on the selected platform type. We first describe the standard properties for each of the above property groups. Following this, details of properties specific to different platform types are detailed.

<a name="platform-user"></a>
######platform -> user properties

`id:` (__required__): The user to use for connecting to the remote platform to run jobs.

`key_file:` OR `password` (__required__ - one or both of these properties MUST be specified):

* `key_file:`: Full path to the private key for connecting to the specified user account.

* `password:`: String password for connecting to the specified user account. _Use of this option, specifying a password in plaintext is not recommended. It is strongly recommended to use passwordless login with an SSH key using the above `key_file` option._

`home:`(optional): The home directory of the user specified by `id`. This is only required when a user account is to be configured as part of a resource configuration process, e.g. when using cloud resources that require configuring.

`public_key:`(optional): A string containing a public key to be installed in the .ssh/authorized_keys file in the home directory of the user specified by `id`.

<a name="platform-service"></a>
######platform -> service properties

`host:` (__required__): The host to connect to for this platform (IP address or hostname). Depending on the platform type, this may refer to a submission node for a batch job system, an endpoint for a public/private cloud platform or the IP/hostname of a standalone server.

`port:` (__required__): The port for the service running on the host identified by the `host` parameter. In the case of a standalone server, for example, this is likely to be 22 for SSH, the same is likely to be true for a batch submission node that would normally be accessed via SSH to issue job submission commands. For a cloud service such as accessing an OpenStack private cloud deployment via its EC2 interface the port may be 8773.

<a name="platform-storage"></a>
######platform -> storage properties

`job_directory:` (__required__): The directory on the remote machine where job files should be stored. Individual job directories named based on the job ID will be created within this location for each job that is run.

<a name="PlatformConfigPBS"></a>
#####Platform Configuration - PBS_PRO Parameters

The following configuration parameters are specific to the `PBS_PRO` platform type.

_There are currently no parameters specific to PBS\_PRO platforms to describe here. A PBS\_PRO platform can be configured using the parameters described [above](#WritingPlatformConfig)._ 

<a name="PlatformConfigSSH"></a>
#####Platform Configuration - SSH_FORK Parameters

The following configuration parameters are specific to the `SSH_FORK` platform type.

_There are currently no parameters specific to SSH\_FORK platforms to describe here. Access to a standalone server using the SSH\_FORK platform type can be configured using the parameters described [above](#WritingPlatformConfig)._ 

<a name="PlatformConfigOS"></a>
#####Platform Configuration - OPENSTACK / OPENSTACK_EC2 / EC2 Parameters

The following configuration parameters are relevant to platforms of the following types: `OPENSTACK`, `OPENSTACK_EC2`, `EC2`.

`platform: -> access_key:` (__required__): The OpenStack access key for the user account to be used for accessing this platform.

`platform: -> secret_key:` (__required__): The OpenStack secret key for the user account to be used for accessing this platform.

`platform: -> user: -> key_name:` (optional): A key name used to specify the public key, pre-registered with the OpenStack system, that will be be configured on cloud resources that are started up on this platform. Registered keys can be listed on the OpenStack platform using the `nova keypair-list` command-line command or via your OpenStack deployment's web interface. This keypair name should provide access to the user account identified by the `id:` parameter.

`platform: -> user: -> public_key:` (optional): A string representing the SSH public key entry to be placed into the _~/.ssh/authorized_keys_ file for the user entry that this key relates to. This is used when creating an account on a remote resource under which jobs can be run.

######platform -> image properties

`preconfigured:` OR `unconfigured:` (__required__ - one or both of these properties MUST be specified): The following three parameters can appear as sub-parameters of `platform: -> image: -> preconfigured:` and `platform: -> image: -> unconfigured:`

 * `id:`: The ID of the image to use. This ID is assigned by the OpenStack platform when an image is registered. You can via registered images and their IDs via the OpenStack web interface or using the command-line command `glance image-list`.
<a name="ImageOSFlavour"></a>
 * `os:`: The operating system of the image, currently accepted values are: `'linux'`, `'windows'`, `'darwin'`, `'solaris'`.
 * `flavour:`: The "flavour" of the operating system. The following values are accepted for the above os values:
   * 'linux': `'ubuntu'`, `'fedora'`, `'redhat'`, `'suse'`
   * 'windows': `'winxp'`, `'win7'`, `'win10'`
   * 'darwin': `'10.8'`, `'10.9'`, `'10.10'`
   * 'solaris': `'10-sparc'`, `'10-x86'`, `'11-sparc'`, `'11-x86'`

The following additional values apply only when specifying an `unconfigured` image type:

 * `admin_key_user:` (__required__): This specifies the admin user name for administrative access to the specified image. This is used when carrying out configuration of the specified image. Since direct root access is often disabled, in the case of linux, this may be a non-root account that allows passwordless access to privileged commands via sudo.

 * `admin_key_file:` (__required__): The key file to use for passwordless SSH access to the admin account identified by `admin_key_user`.

 * `admin_key_name:` (optional): Specifies the name of a key to use when starting a resource on a cloud platform that allows a resource to be dynamically configured with a public key. If specified, this public key will correspond to the private key identified by `admin_key_file`.

######platform -> service properties

`region:` (__required__): A string value specifying the region to use on the target platform. On small scall private cloud deployments, this will be a default region name as defined by the cloud platform. For larger scale public cloud infrastructure, this determines in which region the resource(s) to be started should run in. See documentation for your cloud service to find the available region names.

<a name="PlatformConfigOSExtra"></a>
#####Platform Configuration - additional OPENSTACK Parameters

The following additional parameters apply only to platforms of type `OPENSTACK`:

######platform -> service properties

`auth_url:` (__required__): This specifies the URL for the authentication service provided by the OpenStack platform.

`tenant:` (__required__): This specifies the tenant - the group - that the specified user belongs to and will be authenticated to.

If you have been given an account on an OpenStack cloud platform, the platform administrator will be able to provide you with this information if it is not available through the platform's web-based user interface.

<a name="PlatformConfigExamples"></a>
####Platform Configuration Examples

######An HPC cluster using PBS as its batch submission system

The following is a sample YAML platform configuration for accessing a PBS cluster. Placeholders are used where user or platform-specific information would need to be provided.

```
platform:
    type: PBS_PRO
    id: my-pbs-cluster
    name: My PBS-based HPC Cluster
    service:
        host: <Hostname or IP address for submission node>
        port: 22
    user:
        id: <User ID to connect as>
        key_file: /home/<my user id>/.ssh/my-ssh-keyfile
        # password: # Not recommended but can be provided in 
                    # place of key_file.
    storage:
        # Directory on remote platform for storing job data
        job_directory: <job directory to use>
```

######An OpenStack platform accessed via its EC2 interface

The following is a sample YAML platform configuration for accessing an OpenStack platform via its EC2 interface and using an unconfigured ubuntu machine image. Note that the type and number of resources to use are specified by the user in their job specification.

```
platform:
    type: OPENSTACK_EC2
    id: my-openstack-cloud
    name: My OpenStack Cloud (via EC2 Interface)
    access_key: **************************
    secret_key: **************************
    user:
        id: <user name>
        home: /home/<user name>
        key_file: /home/<user name>/.ssh/my-ssh-keyfile
        public_key: >
         ssh-rsa ********************...
    image:
        unconfigured:
            id: ami-********
            os: linux
            flavour: ubuntu
            admin_key_name: my-cloud-admin-keypair-name
            admin_key_user: root
            admin_key_file: /home/<user-name>/.ssh/cloud_key.pem
    service:
        host: <hostname/IP for cloud service>
        port: 8773
        region: RegionOne
    storage:
        # Directory on remote platform for storing job data
        job_directory: <job directory to use>
```

A similar configuration but using a pre-configured machine image would look like the following:

```
platform:
    type: OPENSTACK_EC2
    id: my-openstack-cloud
    name: My OpenStack Cloud (via EC2 Interface)
    access_key: **************************
    secret_key: **************************
    user:
        id: <user name>
        home: /home/<user name>
        key_name: my-cloud-keypair-name
        key_file: /home/<user name>/.ssh/my-ssh-keyfile
    image:
        preconfigured:
            id: ami-********
            os: linux
            flavour: ubuntu
    service:
        host: <hostname/IP for cloud service>
        port: 8773
        region: RegionOne
    storage:
        # Directory on remote platform for storing job data
        job_directory: <job directory to use>
```

<a name="SoftwareConfiguration"></a>
###Software Configuration

Software Configurations describe an application to be deployed to a resource or group of resources. 

_NOTE: At present, only linux-based deployment is supported. On other platforms, the required application(s) should be pre-installed on the target platform_

As with [Platform Configurations](#PlatformConfiguration), a _Software Configuration_ is also written in [YAML](http://www.yaml.org/spec/1.2/spec.html) format.

Software Configurations provide a set of keys and values to describe the properties of an application and how to deploy it. We now describe the process of writing a software configuration:

<a name="WritingSoftwareConfig"></a>
####Writing a Software Configuration

All software configurations begin with the root node `software:`

`software:` contains five required keys:

 * `id:`: A unique string identifier for the software
 * `name:`: The name of the software
 * `os_type:`: The operating system this software requires. 
 * `os_flavour:`: The specific flavour of operating system that this software requires.
 * `installation:`: Installation contains a set of sub-properties detailing how to deploy the software. These properties are detailed below.

See [details](#ImageOSFlavour) of `os` and `flavour` values for platform configurations for information on the accepted `os_type` and `os_flavour` values.

<a name="software-installation"></a>
######software -> installation properties

`packages:`(__required__): The packages that must be installed for this software.

`package_manager:`(optional): A package manager configuration that is required if packages are not available in standard repositories. This value can take one of the following values:

 * `'apt'`: The [Advance Package Tool](https://wiki.debian.org/Apt) package manager, as used by Debian, Ubuntu and related Linux distibutions.

`<package_manager>_config:` (optional): where \<package_manager\> is replaced with the value specified for the `package_manager` key described above. This provides the ability to offer configuration information specific to different package managers. Sub-keys for the supported package managers are as follows:

 * `apt_config:`
   * ` - source:` (__required__) A list item. One or more sources must be specified for an apt configuration. Each source may have a `key:` key providing a PGP public key to be registered for the remote apt repository.

<a name="SoftwareConfigExamples"></a>
#### Software Configuration Examples

######Configuration for a Linux application with packages in a remote third-party repository

```
software:
    id: my-hpc-app-0.12-linux-ubuntu
    name: My HPC Application
    os_type: linux
    os_flavour: ubuntu
    installation:
        package_manager: apt
        apt_config:
         - source: deb http://<repo hostname/IP>/hpcapp trusty contrib
           key: |
            -----BEGIN PGP PUBLIC KEY BLOCK-----
            Version: GnuPG v1.4.12 (GNU/Linux)
            
            jkjkhsdJKHKJSUKH77889....
            ...
            ...
            ...
            sgd73g4ggG=
            -----END PGP PUBLIC KEY BLOCK-----
    packages:
     - my-hpc-app
     - openmpi-bin
```

<a name="RunningAJob"></a>
## Running a Job

<a name="JobSpecification"></a>
#### Preparing a Job Specification

A job specification is a [YAML](http://www.yaml.org/spec/1.2/spec.html) file used to define a job to be run. The job specification file is passed using the `-j` switch when running a libhpc job using the `libhpc_job_run run` command.

The root of a job specification is the `libhpc_jobspec:` key. This key can take the following sub-keys that define the job to be carried out:

 * `num_processes:`: An integer specifying the number of processes to run this job with (used for parallel job runs). This should be set to 1 for sequential jobs.

 * `executable:`: The full path to the executable _on the remote platform_.

 * `input_files:`: A list of full paths to input files that must be provided as input to the job. These files will be staged to the remote platform.

 * `parameters:`: A list of strings consisting of the parameters to pass to the executable.

 * `stdout:`: Filename to write the job's standard output to. This file will be created in the job directory on the remote platform and returned as part of the output data.

 * `stderr:`: Filename to write the job's standard error output to. This file will be created in the job directory on the remote platform and returned as part of the output data.

 * `output_file_destination:`: The directory on the local machine to store the output data to. This can be '.' for the current directory or a relative path.

For cloud platforms, the following additional values may be specified:

 * `node_type:`: The string identifier for the node type to use, e.g. 'm1.large', 't1.micro', etc..

 * `processes_per_node:`: An integer specifying the number of processes to run on each node. This should be less than or equal to the number of CPU cores provided per node for the specified `node_type`.

######Job Specification Examples

Example of a job specification to run the command 'echo "Hello World!"':

```
libhpc_jobspec:
    num_processes: 1
    executable: /bin/echo
    parameters:
      - "Hello World!"
    stdout: std.out
    stderr: std.err
    output_file_destination: .
```

Example of a job specification to run a parallel file conversion process:

```
libhpc_jobspec:
    node_type: m1.large
    num_processes: 64
    processes_per_node: 8
    input_files: 
        - /home/user/input.data
    parameters:
        - -o output.data
    executable: /usr/bin/fileconvert
    stdout: std.out
    stderr: std.err
    output_file_destination: /tmp/
```

<a name="CommandLineTool"></a>
#### The libhpc\_run\_job Command-line Tool

Jobs can be run from the command-line using the `libhpc_run_job` tool that is installed with the library.

`libhpc_run_job` has two subcommands - `list` and `run`.

The `list` subcommand can take one of two values as an argument:

  * `platforms`: `libhpc_run_job list platforms` lists the IDs of all the registered platforms. These IDs can be used to specify a platform when running a job.
  *  `software`: `libhpc_run_job list software` lists the IDs of all the registered software configurations. These IDs can be used to specify an application to deploy when running a job.

Platform and software configurations are read from YAML files placed in the `.libhpc/config/platform` and `.libhpc/config/software` directories that are created in the user's home directory when installing the library.

The `run` subcommand takes the following switches:

`-p PLATFORM` (__required__): where PLATFORM is a platform ID (the list of IDs can be obtained using the list command) or the full path to YAML file containing a platform configuration.

`-j JOB_SPEC` (__required__): where JOB_SPEC is the full path to a job specification defining the job to run.

`-s SOFTWARE_TO_DEPLOY` (__optional__): where SOFTWARE\_TO\_DEPLOY is the ID of a registered software configuration (the list of available IDs can be obtained using the list command) or the full path to a YAML file containing a software configuration. _This parameter only needs to be provided when the platform configuration defines a cloud platform specifying an unconfigured image._

Help for these commands can be obtained via the command line using one of the following:

```
> libhpc_run_job -h
> libhpc_run_job list -h
> libhpc_run_job run -h
```

######libhpc\_run\_job examples

```
> libhpc_run_job list platforms

Platform configurations:

		my-pbs-cluster
		amazon-ec2-my-creds-unconfigured
		amazon-ec2-my-creds-configured
		openstack-group-account

------------------------------------------------
		
> libhpc_run_job list software

Software configurations:

		my-hpc-app-0.12-linux-ubuntu

------------------------------------------------

> libhpc_run_job run -p amazon-ec2-my-creds-unconfigured \
  -s my-hpc-app-0.12-linux-ubuntu -j ~/my-hpc-app-job-ec2.yaml


> libhpc_run_job run -p my-pbs-cluster -j ~/my-hpc-job-pbs.yaml
```

<a name="DeveloperInfo"></a>
## Developer Information

A developer guide detailing the library's API and how to work with it to integrate the deployer library into other applications will be available shortly.

<a name="Contributors"></a>
## Contributors

This library has been developed by the [libhpc](http://www.imperial.ac.uk/lesc/projects/libhpc) project team based at [Imperial College London](http://www.imperial.ac.uk)

<a name="License"></a>
## License

This tool is licensed under the BSD New (3-Clause) license. See the LICENSE file in the source tree for full details.

<a name="Acknowledgements"></a>
## Acknowledgements

This library and the libhpc methodology have been developed as part of the UK Engineering and Physical Sciences Research Council (EPSRC)-funded libhpc stage I (EP/I030239/1) and II (EP/K038788/1) projects and we would like to thank the EPSRC for supporting this work.