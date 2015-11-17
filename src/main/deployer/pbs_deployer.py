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
Created on 31 Jul 2015

@author: jcohen02
'''
import os
import logging

from deployer.deployment_interface import JobDeploymentBase
from deployer.exceptions import JobError

from saga.filesystem import Directory, File
import saga.job

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class JobDeploymentPBS(JobDeploymentBase):
    '''
    This is a deployer implementation for deploying code to PBS clusters.
    
    This deployer requires a subset of the deployment stages described in the 
    documentation for the base deployer class. The workflow of deployment and 
    job execution used here does not include the start_resources and 
    shutdown_resources stages but implementations are provided for all other 
    phases of the deployment process.   
    '''

    def __init__(self, platform_config):
        '''
        Constructor
        '''
        super(JobDeploymentPBS, self).__init__(platform_config)
        
        # Now we initialise a connection to the remote host using 
        # SAGA-Python. This sets up an SSH connection to the remote cluster's 
        # interactive node.
        ctx = saga.Context("ssh")
        ctx.user_id = self.platform_config.user_id
        ctx.user_key = self.platform_config.user_key_file
        
        # Session is pre-created by superclass
        self.session.add_context(ctx)
        

    def initialise_resources(self, *args, **kwargs):
        JobDeploymentBase.initialise_resources(self)
        # Resource initialisation is not required directly but we use this 
        # function to intiialise the connection with the PBS platform via the 
        # SAGA-Python library.
        self.svc = saga.job.Service('pbs+ssh://%s/'
                                    % self.platform_config.platform_service_host,
                                    session=self.session)
        
        return None        
    
    def deploy_software(self, *args, **kwargs):
        JobDeploymentBase.deploy_software(self)
        # Here we undertake transfer of the code to the remote platform if this 
        # is required. In many cases, the software is likely to already be 
        # deployed on the target platform.
    
    def transfer_files(self):
        JobDeploymentBase.transfer_files(self)
        # Here we transfer any input files to the relevant directory on the 
        # target platform.  
        # Use SAGA-Python to handle the file transfer.
        LOG.debug('Transfer files...')
        job_dir = self.platform_config.storage_job_directory
        host = self.platform_config.platform_service_host
        
        try:
            directory = Directory('sftp://%s%s' % (host, job_dir), 
                                  session=self.session)
        except saga.BadParameter as e:
            LOG.error('The specified job directory does not exist on PBS '
                      'submission node <%s> (%s).' % (host, str(e)))
            raise JobError('The specified job directory does not exist on PBS'
                           'submission node <%s> (%s)' % (host, str(e)))
        
        try:
            # directory.make_dir() does not return a handle to the new directory
            # so need to create the directory URL manually.
            directory.make_dir(self.job_config.job_id)
            job_data_dir = os.path.join(str(directory.url),self.job_config.job_id)  
        except saga.NoSuccess as e:
            LOG.error('The specified job data directory already exists on '
                      'PBS submission node <%s> (%s).' % (host, str(e)))
            raise JobError('The specified job directory already exists on PBS'
                           'submission node <%s> (%s)' % (host, str(e)))
        
        # Now upload the file(s) to the job data directory
        # and create an input file list containing the resulting locations
        # of the files.
        # There are some cases where jobs may not have input files (they may, 
        # for example pull the input files from a remote location as part of 
        # the job process) so we first check whether there are any input files
        # to process, if not, then return from this function
        if not self.job_config.input_files:
            LOG.debug('There are no input files to transfer for this job...')
            return
        
        self.transferred_input_files = []
        for f in self.job_config.input_files:
            try:
                f_obj = File('file://%s' % f, session=self.session)
                f_obj.copy(job_data_dir)
                dest_dir = os.path.join(directory.url.path,self.job_config.job_id)
                self.transferred_input_files.append(
                    os.path.join(dest_dir, 
                    os.path.basename(f_obj.url.path)))
            except:
                LOG.error('Error copying the input file <%s> to the remote '
                          'platform.' % f)
                raise JobError('Error copying the input file <%s> to the '
                               'remote platform.' % f)
        
    def run_job(self, job_details=None):
        JobDeploymentBase.run_job(self)
        # This function uses the SAGA-Python library to run the job. Separate 
        # functionality in the library is used for monitoring the job process.
        
        # TODO: Add modules to PBS job confiuguration
        
        # Here we extract the job details from the previously stored job details
        # object into a SAGA Python job description object so that we can run 
        # the job.
        job_arguments = getattr(self.job_config, 'args', [])
        input_files = getattr(self, 'transferred_input_files', [])
        job_arguments += input_files
        
        jd = saga.job.Description()
        jd.environment = getattr(self.job_config, 'environment', {})
        jd.executable  = getattr(self.job_config, 'executable', None)
        jd.arguments   = job_arguments
        jd.working_directory = getattr(self.job_config, 'working_dir', None)
        jd.output      = getattr(self.job_config, 'stdout', None)
        jd.error       = getattr(self.job_config, 'stderr', None)
        jd.wall_time_limit = getattr(self.job_config, 'time_limit_mins', 0)
        jd.total_cpu_count = getattr(self.job_config, 'num_processes', 1)
        #jd.processes_per_host = 1
        #jd.total_physical_memory = "2400"
        
        self.job = self.svc.create_job(jd)
        self.job.run() 
    
    def wait_for_job_completion(self):
        JobDeploymentBase.wait_for_job_completion(self)
        
        # Wait for job to complete
        self.job.wait()
    
        return (self.job.state, self.job.exit_code)
    
    def collect_output(self, destination):
        JobDeploymentBase.collect_output(self, destination)
        # Here we collect the output from the remote platform when a job has 
        # completed, the output data is transferred to the specified location.
        
