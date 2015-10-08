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
Created on 27 Jul 2015

@author: jcohen02
'''
# TODO: Need to have a think about how best to represent resource credentials.
# Originally had a single set of values for user, key-name and key. This should
# be fine for pre-configured resources where we just need the name of the user
# to log in as and the key to enable this. When we are setting up resources, 
# we'll need root access so should be able to get this through specifying a 
# key key name and associated private-key file for accessing as root or an 
# account where its possible to sudo commands. 

import logging

from deployer.config.platform.base import PlatformConfig

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class OpenStackPlatformConfig(PlatformConfig):
    
    def __init__(self, *args, **kwargs):
        super(OpenStackPlatformConfig, self).__init__(*args, **kwargs)
        self._scheme = 'http'
    
    # EC2/OPENSTACK-specfic properties    
    _key_name = None
    _access_key = None
    _secret_key = None
    _image_id = None
    _image_id_configured = None
    _auth_url = None
    _region = None
    _tenant = None
    
    #===========================================================================
    # PROPERTIES SPECIFIC TO EC2/OPENSTACK PLATFORMS
    #===========================================================================
    
    @property
    def key_name(self):
        return self._key_name
    
    @key_name.setter
    def key_name(self, value):
        self._key_name = value
    
    @property
    def access_key(self):
        return self._access_key
    
    @access_key.setter
    def access_key(self, value):
        self._access_key = value
    
    @property
    def secret_key(self):
        return self._secret_key
    
    @secret_key.setter
    def secret_key(self, value):
        self._secret_key = value

    @property
    def image_id_unconfigured(self):
        return self._image_id
    
    @image_id_unconfigured.setter
    def image_id_unconfigured(self, value):
        self._image_id = value
        
    @property
    def image_id_pre_configured(self):
        return self._image_id_configured
    
    @image_id_pre_configured.setter
    def image_id_pre_configured(self, value):
        self._image_id_configured = value
            
    @property
    def service_auth_url(self):
        return self._auth_url
    
    @service_auth_url.setter
    def service_auth_url(self, value):
        self._auth_url = value
        
    @property
    def service_region(self):
        return self._region
    
    @service_region.setter
    def service_region(self, value):
        self._region = value
        
    @property
    def service_tenant(self):
        return self._tenant
    
    @service_tenant.setter
    def service_tenant(self, value):
        self._tenant = value
    
    def get_info(self):
        basic_conf_str = PlatformConfig.get_info(self)
        os_conf_str = ('Key Name:\t\t%s\nAccess Key:\t\t%s\nSecret Key:\t\t%s\n'
                       'Image ID:\t\t%s\nImage ID Conf\'d:\t%s\nAuth URL:\t\t%s'
                       '\nRegion:\t\t\t%s\nTenant:\t\t\t%s\n' % (self._key_name,
                       self._access_key, self._secret_key, self._image_id,
                       self._image_id_configured, self._auth_url,
                       self._region,self._tenant))
        
        return basic_conf_str + '\n\nOpenStack-specific config:\n' + os_conf_str
    
    def print_info(self):
        LOG.debug('\n\n' + self.get_info())
