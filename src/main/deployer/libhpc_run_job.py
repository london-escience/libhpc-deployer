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
Command line tool to run one or more jobs on the specified platform. 
This tool provides the command line interface to the deployer. Multiple
jobs can be specified by providing a list of job specifications to the -j 
parameter.

This command can exit can exit with the following codes:

   0 - Job(s) completed successfully
   2 - Job specification files missing - one or more of the specified job spec 
       files were not found - no jobs run.
   3 - A job specification file was found but could not be parsed successfully
   4 - Node_type, number of processes or processes per node values don't match 
       for one or more of the jobs specified in the list of job specifications.
   5 - Software deployment error. An error has occurred deploying the specified 
       software on the remote platform.
  10 - Connection error - unable to connect to remote resource via SSH
  11 - Job storage directory not found error - the base job storage directory 
       is not present on the remote platform.
  12 - Job directory already exists error - A directory for the uniquely named 
       job, that is about to be run, already exists.  
 100 - Job error - the job started but failed for some reason 
 
See individual platform deployer implementations for additional exit codes.
 
'''
import os
import pwd
import logging
import argparse

from deployer.config.platform.base import DeployerConfigManager, PlatformConfig
from deployer.config.software.base import SoftwareConfigManager
from deployer.config.job import JobConfiguration
from deployer.core.exceptions import JobConfigurationError, ConnectionError,\
    StorageDirectoryNotFoundError, DirectoryExistsError
from deployer.core.deployment_factory import JobDeploymentFactory
from os.path import expanduser
from deployer.plugins.openstack_ec2_deployer import JobDeploymentEC2Openstack
from deployer.plugins.ec2_deployer import JobDeploymentEC2

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

LIST_INFO_OPTIONS = ['platforms', 'software']

def libhpc_run_job():
    # Begin by checking if the config file directories exist, if not create them
    # expanduser with ~ directly seems to fail when running python process under a different
    # user and the USER and HOME environment variables are not correctly set. Using uid and
    # getpwuid seems to operate correctly to get the username and home directory in
    # these cases.
    uid = os.getuid()
    username = pwd.getpwuid(os.getuid())[0]
    LOG.debug('Looking up user home directory for uid <%s>, username <%s>.' % (uid, username))
    user_home = expanduser('~' + username)
    LOG.debug('Using user home directory <%s>.' % user_home)
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
    run_parser.add_argument('-j', type=str, required=True, dest="job_specs",  
                            nargs="+", help="Full path(s) to one or more job "
                            "specification files defining the job(s) to run.")
    run_parser.add_argument('-s', type=str, required=False, dest="software_to_deploy",
                            help="The software ID or full path to a YAML file "
                            "representing the software to deploy on the "
                            "specified platform.")
    run_parser.add_argument('-i', type=str, required=False, dest="ip_file",
                            help="The full path for a file that should have "
                            "IP addresses of the started cloud nodes written "
                            "to it once the nodes are started and accessible.") 
    run_parser.add_argument('-d', type=str, required=False, dest="done_files_dir",
                            help="Write job done files to the specified "
                            "directory each time a job is complete. Files will "
                            "be named <job_id>_done. This is intended to be "
                            "used with multiple job submission.")
    
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
        job_spec_list = []
        try:
            jobspecs = args.job_specs
            # Now check each of the provided job specs, if any are not 
            # accessible then we fail.
            for jobspec in jobspecs:
                if os.path.isfile(jobspec):
                    # Check if the specified job spec parameter is a YAML file that
                    # we can open.
                    try:
                        job_config = JobConfiguration.from_yaml(jobspec)
                        job_spec_list.append(job_config)
                    except JobConfigurationError as e:
                        LOG.debug('Unable to read the YAML configuration from '
                                  'the specified YAML file <%s>: %s' 
                                  % (jobspec, str(e)))
                        exit(3)
                else:
                    print('\nERROR: Unable to find the specified job '
                          'specification: %s\n' % (jobspec))
                    exit(2)
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

        # Check if we need to write job_done files
        done_files_dir = None
        if args.done_files_dir:
            done_files_dir = args.done_files_dir
            LOG.debug('We have a "done_files" directory specified: <%s>'
                      % done_files_dir)

        ldt.run_job(platform_config, job_spec_list, software_config, 
                    ip_file, done_files_dir)
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
            
    def run_job(self, platform_config_input, job_configs, software_config=None,
                ip_file=None, done_files_dir=None):
        LOG.debug('Received a request to run <%s> job(s) with the platform '
                  'config <%s>.' 
                  % (len(job_configs), platform_config_input))
        if software_config:
            LOG.debug('A software config has also been specified: <%s>' 
                      % (software_config))
        if ip_file:
            LOG.debug('An ip file has been specified: <%s>' 
                      % (ip_file))
        if done_files_dir:
            LOG.debug('A done_files directory has been specified: <%s>' 
                      % (done_files_dir))
        
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
        
        LOG.debug('Deployer instance <%s> obtained successfully...' % d)

        # We specify in the documentation that if more than one job spec is 
        # provided, all jobs in the job spec must have the same values set
        # node_type, num_processes and processes_per_node.
        # We check this now to validate the job specifications provided         
        # At the same time we prepare a list of the job IDs for the jobs to be 
        # run
        job_id_list = []
        node_type_check = job_configs[0].node_type
        np_check = job_configs[0].num_processes
        ppn_check = job_configs[0].processes_per_node
        for spec in job_configs:
            job_id_list.append(spec.job_id)
            if spec.node_type != node_type_check:
                LOG.error('Node type <%s> for job <%s> does not match the '
                          'fixed node type <%s> specified for the first job in '
                          'the list of submitted jobs.'
                          % (spec.node_type, spec.job_id, node_type_check))
                exit(4)
            if spec.num_processes != np_check:
                LOG.error('Number of processes <%s> for job <%s> does not '
                          'match the fixed number of processes <%s> specified ' 
                          'for the first job in the list of submitted jobs.'
                          % (spec.num_processes, spec.job_id, np_check))
                exit(4)
            if spec.processes_per_node != ppn_check:
                LOG.error('Processes per node <%s> for job <%s> does not match '
                          'the fixed processes per node value <%s> specified '
                          'for the first job in the list of submitted jobs.'
                          % (spec.processes_per_node, spec.job_id, ppn_check))
                exit(4)
        
        LOG.debug('Preparing to run the following job(s): <%s> on platform <%s>' 
                  % (job_id_list, platform_config.platform_name))

        
        
                
                
        # We now undertake resource initialisation and we can then iterate
        # over the job specifications running each job on the configured resource(s)
        try:
            # Now that the initial configuration has been done, we can run the job
            # Begin by initialising the resources...
            # Since we mandate that all node_type, num_processes and 
            # processes_per_node values must be the same when multiple job specs are 
            # submitted, we use the values from job_configs[0] for resource init.
            resource_info = d.initialise_resources(node_type=job_configs[0].node_type,
                                                   num_processes=job_configs[0].num_processes,
                                                   processes_per_node=job_configs[0].processes_per_node,
                                                   job_id=job_configs[0].job_id,
                                                   software_config=software_config)
        
            # If an ip file was specified, write the public IPs of the resources
            # to this file. Currently only supports EC2-style cloud platforms
            if ip_file and (isinstance(d, JobDeploymentEC2Openstack) or
                            isinstance(d, JobDeploymentEC2)):
                with open(ip_file, 'w') as f:
                    for node in resource_info:
                        f.write(node[0].public_ips[0] + '\n')
                
            # TODO: Catch any exceptions generated during the software deployment
            # process and exit with return code 5. Resources will be shutdown
            # by the finally statement at the end of this try block.
            if software_config:
                d.deploy_software(software_config)
            else:
                d.deploy_software()
            
                #LOG.error('Error deploying software on remote platform: <%s>' 
                #          % str(e))
                #d.shutdown_resources()
                #exit(5)
                
            # Now that initialisation is complete we can iterate over each
            # of the jobs.
            for job_config in job_configs:
                LOG.debug('Processing job <%s> from list of job configs.' 
                          % job_config.job_id)
                
                job_id = job_config.job_id
            
                if not job_config.working_dir:
                    job_config.working_dir = os.path.join(
                            platform_config.storage_job_directory,
                            job_id)
            
                # TODO: Is it correct to set the job config here or should it be 
                # set on creation of the deployer perhaps, or just passed in to 
                # the various job lifecycle stages? It cannot be set earlier since 
                # it needs to be set per job.
                # Prepare the job configuration
                LOG.debug('Job configuration:\n%s\n' % job_config.get_info())
                d.set_job_config(job_config)
                LOG.debug('Job configuration for job <%s> set on deployer instance '
                          '<%s> obtained successfully...' % (job_config.job_id, d))
                
                try:
                    d.transfer_files()
                    
                    d.run_job()
                    LOG.debug('Waiting for job to finish...')
                    (state, code) = d.wait_for_job_completion()
                    LOG.debug('Finished waiting...State: %s,   Exit code: %s' % (state, code))
                    
                    d.collect_output(job_config.output_file_destination)
                except ConnectionError as e:
                    LOG.error('Connection error when trying to run job: <%s>' % str(e))
                    exit(10)
                except StorageDirectoryNotFoundError as e:
                    LOG.error('The job storage directory specified for the remote '
                              'compute platform does not exist.')
                    exit(11)
                except DirectoryExistsError as e:
                    LOG.error('The job directory for this job already exists.')
                    exit(12)  
                except Exception as e:
                    LOG.debug('Unknown error running this job: <%s>. ' 
                              'Continuing with next job in list.' % str(e))
                
                LOG.debug('Completed job run process for job <%s>.' 
                          % job_config.job_id)
                
                # If we have a done_files directory specified, write the 
                # done file for this job
                if done_files_dir:
                    LOG.debug('Writing job done file for job <%s>' % 
                              job_config.job_id)
                    self._write_done_file(job_config.job_id, done_files_dir)
                else:
                    LOG.debug('Not writing a job done file, no done_file_dir '
                              'specified.')
        finally:
            LOG.debug('Shutting down resources...')
            d.shutdown_resources()
        
        # If an IP file was created, delete it
        if ip_file and os.path.exists(ip_file):
            os.remove(ip_file)
        
        # Remove job done files
        if done_files_dir:
            self._remove_job_done_files(job_id_list, done_files_dir)
        
        LOG.debug('Run job process complete for jobs <%s>' % job_id_list)
        
    def _write_done_file(self, job_id, done_files_dir):
        if not os.path.exists(done_files_dir):
            LOG.debug('Trying to write job done file for job <%s> but done_'
                      'files directory <%s> does not exist.' 
                      % (job_id, done_files_dir))
            return
        if not os.path.isdir(done_files_dir):
            LOG.debug('Trying to write job done file for job <%s> but the '
                      'specified done_files directory <%s> is a file and not a' 
                      ' directory.' % (job_id, done_files_dir))
            return
            
        done_file = os.path.join(done_files_dir, job_id+'_done')
        open(done_file, 'w').close()
        
    def _remove_job_done_files(self, job_id_list, done_files_dir):
        for job_id in job_id_list:
            done_file_path = os.path.join(done_files_dir, job_id+'_done')
            if os.path.exists(done_file_path):
                LOG.debug('Removing job done file <%s>.' % done_file_path)
                os.remove(done_file_path)
            else:
                LOG.debug('Job done file <%s> doesn\'t exist.' % done_file_path)
                
            
if __name__ == '__main__':
    libhpc_run_job()
