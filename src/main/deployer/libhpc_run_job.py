#  Copyright (c) 2015, Imperial College London
#  All rights reserved.
# 
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are met:
# 
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
# 
#  2. Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions and the following disclaimer in the documentation
#     and/or other materials provided with the distribution.
# 
#  3. Neither the name of the copyright holder nor the names of their
#     contributors may be used to endorse or promote products derived from this
#     software without specific prior written permission.
# 
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
#  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
#  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
#  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
#  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
#  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
#  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
#  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
# 
#  -----------------------------------------------------------------------------
# 
#  This file is part of the libhpc-deployer Python library, developed as part
#  of the libhpc projects (http://www.imperial.ac.uk/lesc/projects/libhpc).
# 
#  We gratefully acknowledge the Engineering and Physical Sciences Research
#  Council (EPSRC) for their support of the projects:
#    - libhpc: Intelligent Component-based Development of HPC Applications
#      (EP/I030239/1).
#    - libhpc Stage II: A Long-term Solution for the Usability, Maintainability
#      and Sustainability of HPC Software (EP/K038788/1).
# 
#  -----------------------------------------------------------------------------
'''
This tool provides the command line interface to the deployer. It can exit 
with a number of different exit codes identifying different situations:

  0  - Tool ran and completed successfully
  
  10 - Connection error - unable to connect to remote resource via SSH
  11 - Job storage directory not found error - the base job storage directory 
       is not present on the remote platform.
  12 - Job directory already exists error - A directory for the uniquely named 
       job, that is about to be run, already exists.  
  100 - Job error - the job started but failed for some reason 
'''
import os
import sys
import logging
import argparse

from deployer.config.platform.base import DeployerConfigManager, PlatformConfig
from deployer.config.software.base import SoftwareConfigManager
from deployer.config.job import JobConfiguration
from deployer.exceptions import JobConfigurationError, ConnectionError,\
    StorageDirectoryNotFoundError, DirectoryExistsError
from deployer.deployment_factory import JobDeploymentFactory
from os.path import expanduser
from deployer.openstack_ec2_deployer import JobDeploymentEC2Openstack
from deployer.ec2_deployer import JobDeploymentEC2

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

LIST_INFO_OPTIONS = ['platforms', 'software']

def libhpc_run_job():
    # Begin by checking if the config file directories exist, if not create them
    user_home = expanduser('~')
    platform_config_dir = os.path.join(user_home, '.libhpc','config','platform')
    software_config_dir = os.path.join(user_home, '.libhpc','config','software')
    if not os.path.exists(platform_config_dir):
        os.makedirs(platform_config_dir)
        LOG.debug('Created platform config directory...')
    if not os.path.exists(software_config_dir):
        os.makedirs(software_config_dir)
        LOG.debug('Created software config directory...')
    
    parser = argparse.ArgumentParser(description='Run an HPC job on the '
                                     'specified platform.')
    subparsers = parser.add_subparsers(title='Available subcommands')
    
    list_parser = subparsers.add_parser('list', 
                                help='List registered platforms and software')
    run_parser = subparsers.add_parser('run', help='Run jobs using the '
                                       'specified software and platform.')
    
    
    list_parser.add_argument('info',
                             help="Value can be either 'platforms' or "
                             "'software' to list details of the registered "
                             "compute platforms or software")
    
    run_parser.add_argument('-p', type=str, required=True, dest="platform",
                            help="The ID or full path to a YAML file "
                            "representing the platform to use to run the job.")
    run_parser.add_argument('-j', type=str, required=True, dest="job_spec",
                            help="Full path to a job specification file "
                            "defining the job to run.")
    run_parser.add_argument('-s', type=str, required=False, dest="software_to_deploy",
                            help="The software ID or full path to a YAML file "
                            "representing the software to deploy on the "
                            "specified platform.")
    run_parser.add_argument('-i', type=str, required=False, dest="ip_file",
                            help="The full path for a file that should have "
                            "IP addresses of the started cloud nodes written "
                            "to it once the nodes are started and accessible.")
    
    args = parser.parse_args()
    
    LOG.debug('Args: %s' % str(args))
    
    ldt = LibhpcDeployerTool()
    
    # If the list subcommand has been specified, find out what info to list
    if hasattr(args,'info'):
        try:
            config_names = ldt.list_configuration(args.info)
            if args.info == 'platforms':
                print 'Platform configurations:\n'
            elif args.info == 'software':
                print 'Software configurations:\n'
            for item in config_names:
                print('\t\t%s' % item)
        except ValueError as e:
            LOG.debug('Unable to list configurations: [%s]' % str(e))
            list_parser.print_help()
            exit()
            
    elif hasattr(args, 'platform'):
        # Load the platform configuration
        platform_config = None
        try:
            platform = args.platform
            if os.path.isfile(platform):
                # raise NotImplementedError('Support for using a YAML file '
                #    'describing the platform to use for running a job is not '
                #    'yet implemented. Please use a platform ID instead.')
                # Check if the specified job spec parameter is a YAML file that
                # we can open.
                #try:
                #    job_config = JobConfiguration.from_yaml(jobspec)
                #except JobConfigurationError as e:
                #    LOG.debug('Unable to read the YAML configuration from '
                #              'the specified YAML file <%s>: %s' 
                #              % (jobspec, str(e)))
                dcm = DeployerConfigManager.get_instance()
                conf = dcm.load_platform_config(platform, resource=False)
                platform_config = dcm.read_platform_config(conf)
            elif platform in ldt.dcm.get_platform_names():
                LOG.debug('We have a platform configuration ID <%s> to '
                          'identify the platform to use for running this task.'
                          % (platform))
                platform_config = platform                
            else:
                print('The specified platform file/ID <%s> is not recognised. '
                      % (platform))
                run_parser.print_help()
                exit()
        except ValueError as e:
            LOG.debug('Unable to run job: [%s]' % str(e))
            run_parser.print_help()
            exit()
        
        
        # Load the job specification
        job_config = None
        try:
            jobspec = args.job_spec
            if os.path.isfile(jobspec):
                # Check if the specified job spec parameter is a YAML file that
                # we can open.
                try:
                    job_config = JobConfiguration.from_yaml(jobspec)
                except JobConfigurationError as e:
                    LOG.debug('Unable to read the YAML configuration from '
                              'the specified YAML file <%s>: %s' 
                              % (jobspec, str(e)))
            else:
                print('\nERROR: Unable to find the specified job '
                      'specification: %s\n' % (jobspec))
                exit()
        except ValueError as e:
            LOG.debug('Unable to run job: [%s]' % str(e))
            run_parser.print_help()
            exit()
        
        # Check if we have a software config specified
        software_config = None
        if args.software_to_deploy:
            software_config = args.software_to_deploy
            LOG.debug('We have a software config specified: <%s>' 
                      % software_config)
        
        # Check if an ip file was specified
        ip_file = None
        if args.ip_file:
            ip_file = args.ip_file
            LOG.debug('We have an ip_file specified: <%s>' % ip_file)

        ldt.run_job(platform_config, job_config, software_config, ip_file)
    else:
        parser.print_help()
        LOG.debug('No expected values were present in the parsed input '
                  'data.' % str(e))
        exit()

class LibhpcDeployerTool(object):
    
    def __init__(self):
        self.dcm = DeployerConfigManager.get_instance()
        self.scm = SoftwareConfigManager.get_instance()
        
        self.dcm.init_configuration()
        self.scm.init_configuration()
    
    def list_configuration(self, config_type):
        if config_type not in LIST_INFO_OPTIONS:
            LOG.debug('Config type <%s> is not one of the accepted values '
                      '<%s>' % (config_type, LIST_INFO_OPTIONS))
            raise ValueError('Config type <%s> is not one of the accepted '
                      'values <%s>' % (config_type, LIST_INFO_OPTIONS))
            
        if config_type == 'platforms':
            pns = self.dcm.get_platform_names()
            return pns
        elif config_type == 'software':
            swn = self.scm.get_software_names()
            return swn
        else:
            LOG.debug('Unexpected config type <%s> received.', config_type)
            
    def run_job(self, platform_config_input, job_config, software_config=None,
                ip_file=None):
        LOG.debug('Received a request to run a job with the platform config '
                  '<%s> and job specification <%s>.' 
                  % (platform_config_input, job_config.__dict__))
        if software_config:
            LOG.debug('A software config has also been specified: <%s>' 
                      % (software_config))
        
        # Create a deployment factory and get a deployer for the specified job
        # configuration
        deployment_factory = JobDeploymentFactory()
        d = deployment_factory.get_deployer(platform_config_input)
        
        if isinstance(platform_config_input, PlatformConfig):
            LOG.debug('We\'ve been provided with a pre-instantiated platform config')
            platform_config = platform_config_input
        else:
            LOG.debug('Provided with platform config name. '
                      'Getting platform config from deployer.')
            platform_config = d.get_platform_configuration()
        
        job_id = job_config.job_id
        
        if not job_config.working_dir:
            job_config.working_dir = os.path.join(
                        platform_config.storage_job_directory,
                        job_id)
        
        LOG.debug('Preparing to run job: <%s> on platform <%s>' 
                  % (job_id, platform_config.platform_name))
        
        # TODO: Is it correct to set the job config here or should it be set on 
        # creation of the deployer perhaps, or just passed in to the various
        # Prepare the job configuration
        LOG.debug('Job configuration:\n%s\n' % job_config.get_info())
        d.set_job_config(job_config)
        
        LOG.debug('Deployer instance <%s> obtained and configured '
                  'successfully...' % d)
        
        # Now that the initial configuration has been done, we can run the job
        # Begin by initialising the resources...
        
        resource_info = d.initialise_resources(node_type=job_config.node_type,
                                               num_processes=job_config.num_processes,
                                               processes_per_node=job_config.processes_per_node,
                                               job_id=job_config.job_id,
                                               software_config=software_config)
        
        # If an ip file was specified, write the public IPs of the resources
        # to this file. Currently only supports EC2-style cloud platforms
        if ip_file and (isinstance(d, JobDeploymentEC2Openstack) or
                        isinstance(d, JobDeploymentEC2)):
            with open(ip_file, 'w') as f:
                for node in resource_info:
                    f.write(node[0].public_ips[0] + '\n')
                
        try:
            if software_config:
                d.deploy_software(software_config)
            else:
                d.deploy_software()
            
            d.transfer_files()
            
            d.run_job()
            LOG.debug('Waiting for job to finish...')
            (state, code) = d.wait_for_job_completion()
            LOG.debug('Finished waiting...State: %s,   Exit code: %s' % (state, code))
            
            d.collect_output(job_config.output_file_destination)
            
            #d.shutdown_resources()
        except ConnectionError as e:
            LOG.error('Connection error when trying to run job: <%s>' % str(e))
            sys.exit(10)
        except StorageDirectoryNotFoundError as e:
            LOG.error('The job storage directory specified for the remote '
                      'compute platform does not exist.')
            sys.exit(11)
        except DirectoryExistsError as e:
            LOG.error('The job directory for this job already exists.')
            sys.exit(12)  
        except Exception as e:
            LOG.error('Unknown error running the job: <%s>' % str(e))
            if resource_info:
                LOG.debug('We have node info so there may be nodes to shut '
                          'down...')
            sys.exit(100)
            
        # Finally block will still be run even though sys.exit is called above
        # https://docs.python.org/2/library/sys.html#sys.exit
        finally:
            # If an IP file was created, delete it
            if ip_file and os.path.exists(ip_file):
                os.remove(ip_file)

            d.shutdown_resources()
        
            
if __name__ == '__main__':
    libhpc_run_job()
