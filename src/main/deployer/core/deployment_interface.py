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
import urlparse
import saga
from saga.job import Description, Service
from deployer.core.exceptions import ResourceInitialisationError
from saga.filesystem import File



LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class JobDeploymentBase(object):
    '''
    This is the base interface that all deployment platform plugins must
    adhere to and extend. It provides a set of functions describing a generic  
    workflow for the job deployment process.
    
    Some platforms may not require all the steps in the workflow but this base 
    class provides default implemnetations for cases where a workflow stage  
    is not required and therefore not defined in a plugin class.
    
    The stages of the deployment process are:
    
    start_resources -> initialise_resources -> deploy_software -> 
    transfer_files -> run_job -> collect_output -> shutdown_resources
    
    '''

    platform_config = None
    job_config = None
    running_nodes = None

    def __init__(self, platform_config):
        '''
        This is the base constructor for the job deployment class.
        This will be called by overridden constructors in the platform-specific 
        subclass implementations. 
        '''
        self.platform_config = platform_config

        self.host = self.platform_config.platform_service_host
        self.port = self.platform_config.platform_service_port
        
        self.session = saga.Session(default = False)
    
    def get_platform_configuration(self):
        return self.platform_config
    
    def set_job_config(self, jc):
        self.job_config = jc
    
    def start_resources(self):
        pass
    
    def initialise_resources(self):
        # Check that a job configuration has been provided, we can't proceed 
        # with the job if there is no configuration
        if self.job_config == None:
            raise ResourceInitialisationError('ERROR: No job configuration has '
                    'been provided. Register your job configuration using '
                    'set_job_config() before beginning the job lifecycle.')
    
    def deploy_software(self):
        pass
    
    def transfer_files(self):
        pass
    
    def run_job(self, job_details=None):
        if not self.job_config:
            raise ValueError('The job configuration has not been set, unable '
                             'to run the job without a job configuration.')
    
    def wait_for_job_completion(self):
        pass
    
    def collect_output(self, destination):
        # Here we collect the output from the remote cloud nodes when a job has 
        # completed, the output data is transferred to the specified location 
        # for storage so that it is available for users to collect it after 
        # the cloud resources have been shut down.
        LOG.debug('Collect output...')
        
        
        # TODO: Need to bundle the output files into a tar or similar archive  
        # to pull them back to the host. There may be a large number of files  
        # so this is preferable to pulling each file back separately.
        # For now we pull back files individually
        
        #=======================================================================
        # # ### Looking at running a separate SSH job to bundle the  output
        # # ### files into an archive that can then be transferred back.
        # # ### TODO: Need to find a cross-platform way of handling this.
        #=======================================================================
        
        # Work out whether we have an array of running nodes (e.g. cloud nodes)
        # or whether we're dealing with a single host. If the former is true 
        # then we get the IP/hostname of the target resource from the 
        # running_nodes array, otherwise we can just use the host variable.
        
        remote_host = self.host if not getattr(self, 'running_nodes', None) else self.running_nodes[0][0].public_ips[0]
        LOG.debug('Remote host for file transfer source: %s' % remote_host)
        
        LOG.debug('Preparing output archiving job...')
        archive_file = self.job_config.job_id + '.tar.gz'
        jd = Description()
        jd.environment = getattr(self.job_config, 'environment', {})
        jd.executable  = 'touch'
        jd.arguments   = ['.', ';', 'tar', 'zcvf', archive_file, '*']
        jd.working_directory = getattr(self.job_config, 'working_dir', None)
        self.svc = Service('ssh://%s/' % remote_host, session=self.session)
        self.job = self.svc.create_job(jd)
        LOG.debug('Running output archiving job...')
        self.job.run()
        self.job.wait()
        LOG.debug('Output archiving job complete...')
        
        working_dir = getattr(self.job_config, 'working_dir', None)
        if not working_dir:
            raise ValueError('There is no working directory set. Unable to '
                             'retrieve output files.')
        
        # Get a list of the directories to pull the output files back from
        # TODO: For now we just pull the archive file from the master node
        # but assume that we also need to consider output egnerated on other 
        # nodes.
        output_files = []
        #output_file_dirs = []
        #for node in self.running_nodes:
        #    node_ip = node.public_ips[0]
        #    output_file_dirs.append('sftp://%s%s' % (node_ip, working_dir))
        output_file_archive = 'sftp://%s%s' % (remote_host, 
                                               os.path.join(working_dir, archive_file))
        
        LOG.debug('Output file archive: %s' % output_file_archive)
        
        output_files.append(output_file_archive)
            
        LOG.debug('Got output files: %s' % output_files)
        
        parsed_destination = urlparse.urlparse(destination)
        if parsed_destination.scheme == '':
            destination = 'file://' + destination
        
        for output_file in output_files:
            of = File(output_file, session=self.session)
            of.copy(destination)
    
    def shutdown_resources(self):
        pass