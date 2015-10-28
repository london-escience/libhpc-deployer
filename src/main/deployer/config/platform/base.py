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
Created on 24 Jul 2015

@author: jcohen02
'''
import os
import logging
import yaml
from pkg_resources import resource_listdir, resource_string

from deployer.config import get_platform_config_class

import inspect

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class DeployerConfigManager(object):
    '''
    A manager for the deployer configuration.
    
    When an instance of this class is created, it looks for all the config 
    files in the config.platform package and loads them. A configuration file is 
    a Python class that extends the BasePlatformConfig class defined in 
    this file.
    '''
    _instance = None
    _platforms = {}
    
    # This class follows a singleton pattern, we override __new__ and throw an
    # exception if someone tries to create a class this way. 
    # Instead the class is accessed via the get_instance function.
    def __new__(cls, *args, **kwargs):
        raise Exception('This is a singleton class, use get_instance '
                        ' to access the single instance of this class.')

    def __init__(self):
        LOG.debug('Creating %s class instance...in init...' % __name__)
    
    @classmethod
    def get_instance(cls):
        if cls._instance == None:
            cls._instance = super(DeployerConfigManager, cls).__new__(cls)
            # Manually call init
            cls._instance.__init__()
        return cls._instance
    
    def init_configuration(self):
        (resource_config_files, config_files)  = self.get_platform_config_files()
        
        LOG.debug('Config files: %s' % config_files)
        
        for cf in resource_config_files:
            LOG.debug('Handling resource config file <%s>' % cf)
            
            conf = self.load_platform_config(cf)
            LOG.debug('Config loaded for file <%s>: %s' % (cf, conf))
            parsed_config = self.read_platform_config(conf)
            
            self._platforms[parsed_config.platform_id] = parsed_config
        
        for cf in config_files:
            LOG.debug('Handling config file <%s>' % cf)
            
            conf = self.load_platform_config(cf, resource=False)
            LOG.debug('Config loaded for file <%s>: %s' % (cf, conf))
            parsed_config = self.read_platform_config(conf)
            
            self._platforms[parsed_config.platform_id] = parsed_config
        
        platform_names = self.get_platform_names()
        platform_list = ''
        for n in platform_names:
            platform_list += ("Platform:\t%s\n" % n)
        LOG.debug('Registered platforms: \n' + platform_list)
        
    def get_platform_config_files(self):
        resource_config_files = [x for x in resource_listdir(
                        'deployer.config.platform','') if x.endswith('.yaml')]
        
        platform_userdir = os.path.expanduser('~/.libhpc/config/platform')
        config_files=[]
        if os.path.exists(platform_userdir):
            config_files = [os.path.join(platform_userdir,x) for x in 
                                    os.listdir(platform_userdir) if 
                                    x.endswith('.yaml')]
        
        LOG.debug("Found resource config files: %s" % resource_config_files)
        LOG.debug("Found standard config files: %s" % config_files) 

        return (resource_config_files, config_files)
    
    def load_platform_config(self, conf_file, resource=True):
        # Parse the specified config file into a dictionary
        if resource:
            conf = yaml.load(resource_string('deployer.config.platform', conf_file))
        else:
            with open(conf_file, 'r') as f:
                conf = yaml.load(f.read())
        platform_conf = conf['platform']
        LOG.debug('Read configuration for platform <%s>...' % platform_conf['name'])
        return conf
    
    def read_platform_config(self, pc):
        # Load the provided platform config into an instance of the config class
        # Get the platform type from the config and get a ref to the class obj
        LOG.debug('Reading config for platform: %s' % pc['platform']['name'])
        
        platform_type = pc['platform']['type']
        
        cls = get_platform_config_class(platform_type)
        if cls == None:
            raise TypeError('A configuration class is not available for '
                            'platforms of type <%s>' % platform_type)
        config = cls(pc['platform']['type'], pc['platform']['id'],  
                     pc['platform']['name'], pc['platform']['service'].get('host', None), 
                     pc['platform']['service'].get('port', None))
    
        # Now handle all the parameters that are specific to this type of class
        # To do this, we walk through the parameters from the YAML file, 
        # setting these on the configuration class. 
        property_list = self._get_config_properties(cls)
        
        LOG.debug('PROPERTY_LIST:\n\n%s' % property_list)
        
        # Now walk through the YAML, check if a property exists in 
        # the property_list - if a property exists, set it on the configuration
        # object.
        config_items = self._get_yaml_config_items(pc['platform'])
        
        LOG.debug('CONFIG_ITEMS:\n\n%s' % config_items)
        
        # Iterate through config items, if item doesn't start with platform_
        # then its not a base value and won't have been set yet. Get the 
        # function attribute from the class and call it with the value to set
        # the value on the property.
        for k, v in config_items.iteritems():
            if not k.startswith('platform_') and k in property_list:
                property_set = False
                for c in config.__class__.mro():
                    if (k in c.__dict__) and (type(c.__dict__[k]) == type(property())):
                        # Get the setter function for the attribute and set val
                        func = c.__dict__[k].__set__
                        func(config, v)
                        property_set = True
                        break
                if not property_set:
                    LOG.error('An unsupported property <%s> was found...' % k)
            else:
                LOG.warning('Ignoring platform property <%s>' % k)
        
        return config
    
    def load_platform_configs(self):
        # Load all platform configurations and store them as a class in the 
        # _platforms array.
        files = self.get_platform_config_files()
        for f in files:
            pc = self.load_platform_config(f)
            conf_obj = self.read_platform_config(pc)
            self._platforms[conf_obj.name] = conf_obj
    
    def get_platform_names(self):
        return self._platforms.keys()
    
    def get_platform_configuration(self, name):
        try:
            return self._platforms[name]
        except KeyError:
            raise ValueError('A platform with the ID <%s> is not registered '
                             'with this configuration manager.' % name)

    
    def _get_config_properties(self, config_class):
        # Get the full set of configuration properties from the target 
        # configuration class.
        # Check we received a class instance
        if not inspect.isclass(config_class):
            raise TypeError('This function must be called with a PlatformConfig'
                            ' class object, not an instance of a class.')
        
        # First get the superclass(es) for the provided class
        classes = [c for c in config_class.__bases__]
        classes.append(config_class)
        LOG.debug('Looking for config properties in these '
                  'classes <%s>' % classes)
        
        props = []
        for cl in classes:
            for p in cl.__dict__.keys():
                if type(cl.__dict__[p]) == type(property()):
                    props.append(p)
                    LOG.debug('Added property <%s> to the prop list...' % p)
        
        return props
    
    def _get_yaml_config_items(self, yaml_obj):
        # Get all the properties from the YAML document and return them
        # as a flat dictionary
        items = {}
        def get_values(obj, key_base=''):
            for k, v in obj.iteritems():
                if type(v) == type(dict()):
                    base_str = k if key_base == '' else key_base + '_' + k
                    get_values(v, base_str)
                else:
                    #new_key = key_base + '_' + k if key_base != '' else 'platform_' + k
                    new_key = key_base + '_' + k if key_base != '' else k
                    # service_host and service_port are special cases for now...
                    if new_key in ['service_host', 'service_port', 'id', 'name', 'type']:
                        new_key = 'platform_' + new_key
                    #LOG.debug("Key: %s,   Value: %s\n\n" % (new_key, v))
                    items[new_key] = v
        get_values(yaml_obj)
        return items
        
    
class PlatformConfig(object):
    # The connection 'scheme' for the platform connection URL - 
    # This is set by subclasses.
    _scheme = None
    #supported_types = ['OPENSTACK','REMOTE_SSH','LOCAL']
    _platform_type = None
    _platform_id = None
    _platform_name = None
    _platform_host = None
    _platform_port = None
    
    _user_id = None
    _user_key_file = None
    _user_home = None
    _user_password = None

    _storage_job_directory = None
    
    #ec2_os_platforms = ['OPENSTACK','EC2']

    def __init__(self, ptype, pid, pname, phost, pport = None):
        #if ptype.upper() not in self.supported_types:
        #    raise ValueError('The specified platform type <%s> is not '
        #                     'supported.' % ptype)
        self._platform_type = ptype.upper()
        self._platform_id = pid
        self._platform_name = pname
        self._platform_host = phost
        self._platform_port = pport
    
    @property
    def scheme(self):
        return self._scheme
    
    @property
    def platform_type(self):
        return self._platform_type
    
    @property
    def platform_id(self):
        return self._platform_id
    
    @property
    def platform_name(self):
        return self._platform_name
    
    @property
    def platform_service_host(self):
        return self._platform_host
    
    @property
    def platform_service_port(self):
        return self._platform_port
    
    @property
    def user_id(self):
        return self._user_id
    
    @user_id.setter
    def user_id(self, value):
        self._user_id = value

    @property
    def user_home(self):
        return self._user_home
    
    @user_home.setter
    def user_home(self, value):
        self._user_home = value
        
    @property
    def user_key_file(self):
        return self._user_key_file
    
    @user_key_file.setter
    def user_key_file(self, value):
        self._user_key_file = value
        
    @property
    def user_password(self):
        return self._user_password
    
    @user_password.setter
    def user_password(self, value):
        self._user_password = value
    
    @property
    def storage_job_directory(self):
        return self._storage_job_directory
    
    @storage_job_directory.setter
    def storage_job_directory(self, value):
        self._storage_job_directory = value

    def get_info(self):
        conf_str = ('Type:\t\t%s\nID:\t\t%s\nName:\t\t%s\nHost:\t\t%s\n'
                    'Port:\t\t%s\nJob directory:\t\t%s' 
                    % (self._platform_type, self._platform_id, self._platform_name, 
                       self._platform_host, self._platform_port,
                       self._job_directory))
        return conf_str
    
    def print_info(self):
        conf_str = self.get_info()
        LOG.debug('\nBASE CONFIG INFO:\n----------------\n%s' % conf_str)
        
# Main function for testing
if __name__ == '__main__':
    cfg_man = DeployerConfigManager.get_instance()

    cfg_man.init_configuration()
     
    platform_names = cfg_man.get_platform_names()
    print "Registered platforms: \n"
    for n in platform_names:
        print "\tPlatform: %s" % n
    print '\n\n'
     
    for n in platform_names:
        pc = cfg_man.get_platform_configuration(n)
        pinfo = pc.get_info()
        print "Info for platform <%s>:\n\n%s\n\n" % (n, pinfo)
