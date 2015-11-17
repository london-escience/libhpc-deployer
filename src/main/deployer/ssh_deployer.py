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

SSH deployer. Uses saga-python to provide access to run jobs on a standalone 
resource.
'''
import logging
import os
import saga.job

from deployer.deployment_interface import JobDeploymentBase
from deployer.exceptions import JobError

from saga.filesystem import Directory, File, RECURSIVE

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class JobDeploymentSSH(JobDeploymentBase):
    '''
    This is a deployer implementation for deploying code and running jobs on 
    local or remote resources via an SSH connection using the SAGA-Python  
    library.  
    '''
    # The libcloud driver for OpenStack, configured in the constructor
    driver = None

    def __init__(self, platform_config):
        '''
        Constructor
        '''
        super(JobDeploymentSSH, self).__init__(platform_config)
        
        # Here we set up the basic platform configuration properties so that
        # we can access the target resource via SSH
        self.host = self.platform_config.platform_service_host
        if self.platform_config.platform_service_port:
            self.port = self.platform_config.platform_service_port
        else:
            self.port = 22
        
        # Now we set up a SAGA-Python session to handle file transfer
        ctx = saga.Context("ssh")
        ctx.user_id = self.platform_config.user_id
        ctx.user_key = self.platform_config.user_key_file

        # Session is pre-created by superclass
        self.session.add_context(ctx)
        
    def initialise_resources(self, *args, **kwargs):
        JobDeploymentBase.initialise_resources(self)
        LOG.debug('SSH Deployer: Initialise resources - Nothing to do here...')
        
        return None

    def deploy_software(self):
        JobDeploymentBase.deploy_software(self)
        # Here we undertake transfer of the code to the remote platform if this 
        # is required. In many cases, the software is likely to already be 
        # deployed on the target platform or may have been configured via a 
        # tool such as cloud-init, puppet, etc at resource initialisation time.
        LOG.debug('SSH Deployer: Deploy software...')
    

    def transfer_files(self):
        JobDeploymentBase.transfer_files(self)
        LOG.debug('SSH Deployer: Transfer files...')
        # Here we transfer any input files to the relevant directory on the 
        # target platform. 
        # Use SAGA-Python to handle the file transfer.
        job_dir = self.platform_config.storage_job_directory
        # Check that the job storage directory exists and then create a 
        # sub-directory specifically for this job.
        try:
            LOG.debug('URL for file transfer: <sftp://%s:%s%s>' 
                      % (self.host, self.port, job_dir))
            directory = Directory('sftp://%s:%s%s' % (self.host, self.port, 
                                  job_dir), session=self.session)
        except saga.BadParameter as e:
            LOG.error('The specified job directory does not exist on resource '
                      '<%s> (%s).' % (self.host, str(e)))
            raise JobError('The specified job directory does not exist '
                           'on resource <%s> (%s)' % (self.host, str(e)))
        try:
            # directory.make_dir() does not return a handle to the new directory
            # so need to create the directory URL manually.
            directory.make_dir(self.job_config.job_id)
            job_data_dir = os.path.join(str(directory.url),self.job_config.job_id)  
        except saga.NoSuccess as e:
            LOG.error('The specified job data directory already exists on '
                      'resource <%s> (%s).' % (self.host, str(e)))
            raise JobError('The specified job directory already exists on '
                           'on resource <%s> (%s)' % (self.host, str(e)))
        
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

    def run_job(self):
        JobDeploymentBase.run_job(self)
        # TODO: Should this be running/managing the job remotely via a SAGA
        # SSH session or should we be expecting to communicate with a remote 
        # resource management service to handle this?
        
        # This function could use the libhpc resource daemon client to talk to  
        # a resource daemon that is installed on the target resource, however,  
        # at present we simply use SSH (via SAGA Python) to trigger job   
        # execution and handle compressing and returning the output files. 
        LOG.debug('SSH Deployer: Run job...')
        
        job_arguments = getattr(self.job_config, 'args', [])
        input_files = getattr(self, 'transferred_input_files', [])
        job_arguments += input_files
        
        # Check if we have a JOB_ID variable in the arguments or input files.
        # If so, replace this variable with the actual job ID.
        job_arguments_tmp = job_arguments
        job_arguments = []
        for item in job_arguments_tmp:
            job_arguments.append(item.replace('$JOB_ID', self.job_config.job_id))
        
        LOG.debug('Modified job arguments: %s' % job_arguments)
        
        jd = saga.job.Description()
        jd.environment = getattr(self.job_config, 'environment', {})
        jd.executable  = getattr(self.job_config, 'executable', None)
        jd.arguments   = job_arguments
        jd.working_directory = getattr(self.job_config, 'working_dir', None)
        jd.output      = getattr(self.job_config, 'stdout', None)
        jd.error       = getattr(self.job_config, 'stderr', None)
        jd.wall_time_limit = getattr(self.job_config, 'time_limit_mins', 0)
        
        if not jd.output:
            jd.output = 'std.out'
        if not jd.error:
            jd.error = 'std.err'
        
        self.svc = saga.job.Service('ssh://%s/' % self.host, session=self.session)
        self.job = self.svc.create_job(jd)
        self.job.run()
        
    def wait_for_job_completion(self):
        LOG.debug('SSH Deployer: Waiting for job completion...')
        self.job.wait()
        LOG.debug('SSH Deployer: Job has finished...')
        return (None, None)

    def collect_output(self, destination):
        # We're using the default implementation of the file transfer code
        # This doesn't take into account a different port for the remote host
        # connection. To work around this, we temporarily set the host property
        # to include the port and the revert to the original value after the
        # file transfer is complete.
        host_tmp = self.host
        self.host = ('%s:%s' % (self.host, self.port)) 
        
        # Using the base implementation of job output file collection...
        JobDeploymentBase.collect_output(self, destination)
        
        # If job_config delete_job_files is True, we can now delete the job
        # files on the remote platform
        if self.job_config.delete_job_files:
            jobs_dir = self.platform_config.storage_job_directory
            # Check that the job storage directory exists and then create a 
            # sub-directory specifically for this job.
            try:
                LOG.debug('URL for file job directory: sftp://%s%s' 
                          % (self.host, jobs_dir))
                directory = Directory('sftp://%s%s' % (self.host, jobs_dir), 
                                      session=self.session)
            except saga.BadParameter as e:
                LOG.error('The specified job directory does not exist on '
                          'resource <%s> (%s).' % (self.host, str(e)))
                raise JobError('The specified job directory does not exist '
                               'on resource <%s> (%s)' % (self.host, str(e)))
            try:
                LOG.debug('Deleting job directory after job completion '
                          '<sftp://%s%s/%s>' % (self.host, jobs_dir, 
                                                self.job_config.job_id))
                directory.remove(self.job_config.job_id, RECURSIVE)
            except saga.NoSuccess as e:
                LOG.error('The specified job data directory couldn\'t be '
                          'removed <%s> (%s).' % (self.job_config.job_id, str(e)))
                raise JobError('The specified job data directory couldn\'t be '
                               'removed <%s> (%s)' % (self.job_config.job_id, str(e)))

        # Set the host value back to its original value
        self.host = host_tmp
        
    def shutdown_resources(self):
        JobDeploymentBase.shutdown_resources(self)
        # Here we collect terminate the running resources for this job and 
        # wait until they have been shut down.
        LOG.debug('SSH Deployer: Shutdown resources - nothing to do here.')
