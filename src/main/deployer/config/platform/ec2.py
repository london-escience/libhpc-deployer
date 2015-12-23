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
import logging

from deployer.config.platform.base import PlatformConfig

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class EC2PlatformConfig(PlatformConfig):
    
    def __init__(self, *args, **kwargs):
        super(EC2PlatformConfig, self).__init__(*args, **kwargs)
        self._scheme = 'http'
    
    # EC2/OPENSTACK-specific properties
    _access_key = None
    _secret_key = None
    
    _user_key_name = None
    _user_public_key = None
    
    _image_preconfigured = None
    _image_unconfigured = None
    _region = None
    
    _image_preconfigured_id = None
    _image_preconfigured_os = None
    _image_preconfigured_flavour = None
    _image_unconfigured_id = None
    _image_unconfigured_os = None
    _image_unconfigured_flavour = None
    _image_unconfigured_admin_key_name = None
    _image_unconfigured_admin_key_user = None
    _image_unconfigured_admin_key_file = None
    
    #===========================================================================
    # PROPERTIES SPECIFIC TO EC2/OPENSTACK PLATFORMS
    #===========================================================================
        
    @property
    def access_key(self):
        return self._access_key
    
    # TODO: Having issues with cloud library returning unexpected errors if 
    # access/secret key are set here to None. For now, ensuring that if there 
    # an attempt to set these values to None, they are set to empty string.
    @access_key.setter
    def access_key(self, value):
        if not value:
            self._access_key = ''
        else:
            self._access_key = value
    
    @property
    def secret_key(self):
        return self._secret_key
    
    @secret_key.setter
    def secret_key(self, value):
        if not value:
            self._secret_key = ''
        else:
            self._secret_key = value

    @property
    def user_key_name(self):
        return self._user_key_name
    
    @user_key_name.setter
    def user_key_name(self, value):
        self._user_key_name = value

    @property
    def user_public_key(self):
        return self._user_public_key
    
    @user_public_key.setter
    def user_public_key(self, value):
        self._user_public_key = value

    @property
    def image_preconfigured_id(self):
        return self._image_preconfigured_id
    
    @image_preconfigured_id.setter
    def image_preconfigured_id(self, value):
        self._image_preconfigured_id = value

    @property
    def image_preconfigured_os(self):
        return self._image_preconfigured_os
    
    @image_preconfigured_os.setter
    def image_preconfigured_os(self, value):
        self._image_preconfigured_os = value
        
    @property
    def image_preconfigured_flavour(self):
        return self._image_preconfigured_flavour
    
    @image_preconfigured_flavour.setter
    def image_preconfigured_flavour(self, value):
        self._image_preconfigured_flavour = value
            
    @property
    def image_unconfigured_id(self):
        return self._image_unconfigured_id
    
    @image_unconfigured_id.setter
    def image_unconfigured_id(self, value):
        self._image_unconfigured_id = value
    
    @property
    def image_unconfigured_os(self):
        return self._image_unconfigured_os
    
    @image_unconfigured_os.setter
    def image_unconfigured_os(self, value):
        self._image_unconfigured_os = value

    @property
    def image_unconfigured_flavour(self):
        return self._image_unconfigured_flavour
    
    @image_unconfigured_flavour.setter
    def image_unconfigured_flavour(self, value):
        self._image_unconfigured_flavour = value
        
    @property
    def image_unconfigured_admin_key_name(self):
        return self._image_unconfigured_admin_key_name
    
    @image_unconfigured_admin_key_name.setter
    def image_unconfigured_admin_key_name(self, value):
        self._image_unconfigured_admin_key_name = value
        
    @property
    def image_unconfigured_admin_key_file(self):
        return self._image_unconfigured_admin_key_file
    
    @image_unconfigured_admin_key_file.setter
    def image_unconfigured_admin_key_file(self, value):
        self._image_unconfigured_admin_key_file = value
        
    @property
    def image_unconfigured_admin_key_user(self):
        return self._image_unconfigured_admin_key_user
    
    @image_unconfigured_admin_key_user.setter
    def image_unconfigured_admin_key_user(self, value):
        self._image_unconfigured_admin_key_user = value
                
    @property
    def service_region(self):
        return self._region
    
    @service_region.setter
    def service_region(self, value):
        self._region = value

    def get_info(self):
        basic_conf_str = PlatformConfig.get_info(self)
        os_conf_str = ('Key Name:\t\t%s\nPublic Key:\t\t%s\nAccess Key:\t\t%s\n'
                       'Secret Key:\t\t%s\n'
                       'Image ID:\t\t%s\n\tImage OS:\t\t%s\n\tImage flavour:\t\t'
                       '%s\nAdmin key name:\t%s\nAdmin key file:\t%s\nAdmin '
                       'user:\t\t%s\nImage ID Conf\'d:\t%s\n\tImage OS:\t\t%s\n'
                       '\tImage flavour:\t\t%s'
                       '\nRegion:\t\t\t%s' 
                       % (self._user_key_name, self._user_public_key,
                       self._access_key, self._secret_key, 
                       self._image_unconfigured_id, self._image_unconfigured_os,
                       self._image_unconfigured_flavour,
                       self._image_unconfigured_admin_key_name,
                       self._image_unconfigured_admin_key_file,
                       self._image_unconfigured_admin_key_user,  
                       self._image_preconfigured_id, 
                       self._image_preconfigured_os,
                       self._image_preconfigured_flavour, self._region))
        
        return basic_conf_str + '\n\nOpenStack-specific config:\n' + os_conf_str
    
    def print_info(self):
        LOG.debug('\n\n' + self.get_info())
        
# Not using this class at present but this may be a good way to tidy up the 
# configuration for the above properties.
class ImageConfig(object):
    _preconfigured = False
    _id = None
    _os = None
    _flavour = None
    _key_name = None
    _key_user = None
    _key_file = None
    
    def __init__(self, preconfigured, img_id, os, flavour, 
                 key_user = None, key_file = None, key_name = None):
        self._preconfigured = preconfigured
        self._id = img_id
        self._os = os
        self._flavour = flavour
        self._key_user = key_user
        self._key_file = key_file
        self._key_name = key_name
        
    @property
    def preconfigured(self):
        return self._preconfigured
    
    @property
    def id(self):
        return self._id
    
    @property
    def os(self):
        return self._os
    
    @property
    def flavour(self):
        return self._flavour
    
    @property
    def key_user(self):
        return self._key_user
    
    @property
    def key_file(self):
        return self._key_file

    @property
    def key_name(self):
        return self._key_name
    
    def get_info(self):
        image_conf_str = ('Image:\t\t%s\n\tID:\t\t%s\n\tPreconfigured?:\t\t%s\n'
                          '\tOS:\t\t%s\n\tFlavour:\t\t%s\n'
                          '\tKey User:\t%s\n\tKey File:\t%s\n\tKey Name:\t%s\n'
                          % (self.id, self.preconfigured, self.os, self.flavour,
                             self.key_user, self.key_file, self.user_key_name,
                             self.user_public_key))
                       
        return image_conf_str
    
    def print_info(self):
        LOG.debug('\n\n' + self.get_info())
