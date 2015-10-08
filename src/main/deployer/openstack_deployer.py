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

OpenStack deployer.

*** NOTE: ***: This class is still in development. For OpenStack platforms, 
               please use the EC2 interface via the resource type OPENSTACK_EC2.

'''
import logging
import socket

import saga
import saga.job

from libcloud.security import VERIFY_SSL_CERT
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from deployer.deployment_interface import JobDeploymentBase
from deployer.exceptions import ResourceInitialisationError

from deployer.utils import generate_instance_id

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class JobDeploymentOpenstack(JobDeploymentBase):
    '''
    This is a deployer implementation for deploying code and running jobs on 
    OpenStack cloud resources.
    
    The workflow of deployment and job execution used here covers all the 
    stages set out in the base deployer class so all functions from the base 
    class are overloaded.  
    '''
    # The libcloud driver for OpenStack, configured in the constructor
    driver = None

    def __init__(self, platform_config):
        '''
        Constructor
        '''
        raise NotImplementedError('The OpenStack deployer is still under '
                                  'development. To use an OpenStack platform '
                                  'with this library, please use the OpenStack '
                                  'platform\'s EC2 interface via the ' 
                                  'OPENSTACK_EC2 resource type ')
        
        super(JobDeploymentOpenstack, self).__init__(platform_config)
        
        # Here we set up Apache libcloud with the necessary config obtained
        # from the job config
        # Prepare the necessary config information from the job config object.
        user_name = self.job_config.user_id
        user_pass = self.job_config.user_password
        host = self.job_config.platform_service_host
        port = self.job_config.platform_service_port
        region = self.job_config.service_region
        tenant = self.job_config.service_tenant
        auth_url = self.job_config.service_auth_url
        
        VERIFY_SSL_CERT = False

        OpenStack = get_driver(Provider.OPENSTACK)
        self.driver = OpenStack(user_name, user_pass, host=host, port=port,
                       ex_force_service_region=region,
                       ex_force_auth_url=auth_url,
                       ex_force_auth_version='2.0_password',
                       ex_tenant_name=tenant)
        
    def initialise_resources(self, resource_config=None, num_resources=1,
                             resource_type='m1.small', job_id=None):
        JobDeploymentBase.initialise_resources(self)
        # Start up the cloud resources here and wait for them to reach the 
        # running state. Need to know the image ID that we're starting. The
        # image ID is available from the job configuration
        image_id = None
        image_id_configured = self.job_config.image_id_pre_configured
        image_id_unconfigured = self.job_config.image_id_unconfigured
        
        if image_id_configured and not image_id_unconfigured:
            image_id = image_id_configured
            LOG.debug('Only a configured image identifier has been provided, '
                      'using image ID <%s>.' % image_id)
        elif (not image_id_configured) and image_id_unconfigured:
            if not resource_config:
                LOG.error('Only an unconfigured image ID provided but '
                          'no resource configuration has been provided.')
                raise ResourceInitialisationError('ERROR: Only an unconfigured '
                                        'image type is available but no image '
                                        'configuration has been provided.')
            image_id = image_id_unconfigured
            LOG.debug('Only an unconfigured image identifier has been '
                      'provided, using image ID <%s>.' % image_id)
        elif image_id_configured and image_id_unconfigured:
            image_id = image_id_unconfigured if resource_config else image_id_configured
            LOG.debug('Both configured and unconfigured images provided, '
                      'using image ID <%s>.' % image_id)
        else:
            raise ResourceInitialisationError('ERROR: No image information '
                             'available in the platform configuration, unable '
                             'to initialise resources.')
            
        # Check that the image is present and then use the libcloud driver to  
        # start the resources and return once they're running. 
        # TODO: This is currently synchronous but could also be done  
        # asynchronously using a callback to notify the caller when the nodes 
        # are ready. 
        
        #images = self.driver.list_images()
        #img = next((i for i in images if i.id == image_id), None)
        #if not img:
        
        try:
            img = self.driver.get_image(image_id)
        except socket.error as e:
            img = None
            raise ResourceInitialisationError('ERROR contacting the remote '
                             'cloud platform. Do you have an active network '
                             'connection? - <%s>' % str(e))
        except:
            img = None
            raise ResourceInitialisationError('ERROR: The specified image <%s> '
                             'is not present on the target platform, unable '
                             'to start resources.' % image_id)
        
        sizes = self.driver.list_sizes()
        size = next((s for s in sizes if s.name == resource_type), None)
        if not size:
            raise ResourceInitialisationError('ERROR: The specified resource '
                             'size <%s> is not present on the target platform. '
                             'Unable to start resources.' % resource_type)
        
        # Get the keypair name from the configuration
        keypair_name = self.job_config.key_name
        
        # At this point we know that the image is available and the specified 
        # resource type is valid so we can request to start the instance(s)
        LOG.debug('About to start <%s> resources of type <%s> based on image '
                  '<%s (%s)> with keypair <%s>.' % (num_resources, size.name, 
                  img.id, img.name, keypair_name))
        
        # When starting a resource we need the name, image, type, keypair, 
        # configuration data and details of the number of resources to start.
        name = job_id
        if not name:
            name = generate_instance_id()
        
        self.driver.create_node(name=name, image=img, size=size, 
                                ex_keyname=keypair_name)
        return
        
    def deploy_software(self):
        JobDeploymentBase.deploy_software(self)
        # Here we undertake transfer of the code to the remote platform if this 
        # is required. In many cases, the software is likely to already be 
        # deployed on the target platform or may have been configured via a 
        # tool such as cloud-init, puppet, etc at resource initialisation time.
    
    def transfer_files(self):
        JobDeploymentBase.transfer_files(self)
        # Here we transfer any input files to the relevant directory on the 
        # target platform. 
    
    def run_job(self, job_details=None):
        JobDeploymentBase.run_job(self)
        # This function uses the libhpc resource daemon client to talk to the 
        # resource daemon that is installed on cloud resources. It uses this 
        # interface to run jobs and monitor their state to see when they are 
        # complete. 
        
        
    def collect_output(self):
        JobDeploymentBase.collect_output(self)
        # Here we collect the output from the remote cloud nodes when a job has 
        # completed, the output data is transferred to the specified location 
        # for storage so that it is available for users to collect it after 
        # the cloud resources have been shut down.
