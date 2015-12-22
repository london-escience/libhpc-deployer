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

Base configuration for software package information (to allow deployment)
'''
import os
import logging
import pwd
import yaml
from pkg_resources import resource_listdir, resource_string

from deployer.config import get_software_config_class

import inspect

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class SoftwareConfigManager(object):
    '''
    A manager for handling software configurations.
    
    When an instance of this class is created, it looks for all the config 
    files in the config.software package and loads them. A configuration file is 
    a Python class that extends the base SoftwareConfig class defined in 
    this file.
    '''
    _instance = None
    _software = {}
    
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
            cls._instance = super(SoftwareConfigManager, cls).__new__(cls)
            # Manually call init
            cls._instance.__init__()
        return cls._instance
    
    def init_configuration(self):
        (resource_config_files, config_files) = self.get_software_config_files()
        
        LOG.debug('Config files: %s' % config_files)
        
        for cf in resource_config_files:
            LOG.debug('Handling resource config file <%s>' % cf)
             
            conf = self.load_software_config(cf)
            LOG.debug('Config loaded for resource file <%s>: %s' % (cf, conf))
            parsed_config = self.read_software_config(conf)
            
            self._software[parsed_config.software_id] = parsed_config
        
        for cf in config_files:
            LOG.debug('Handling resource config file <%s>' % cf)
             
            conf = self.load_software_config(cf, resource=False)
            LOG.debug('Config loaded for file <%s>: %s' % (cf, conf))
            parsed_config = self.read_software_config(conf)
            
            self._software[parsed_config.software_id] = parsed_config
        
        software_names = self.get_software_names()
        software_list = ''
        for n in software_names:
            software_list += ("Software:\t%s\n" % n)
        LOG.debug('Registered software: \n' + software_list)
        
    def get_software_config_files(self):
        resource_config_files = [x for x in resource_listdir(
                        'deployer.config.software','') if x.endswith('.yaml')]
        
        # expanduser with ~ directly seems to fail when running python process under a different
        # user and the USER and HOME environment variables are not correctly set. Using uid and
        # getpwuid seems to operate correctly to get the username and home directory in 
        # these cases.
        uid = os.getuid()
        username = pwd.getpwuid(os.getuid())[0]

        software_userdir = os.path.expanduser('~%s/.libhpc/config/software' % username)
        config_files = []
        if os.path.exists(software_userdir):
            config_files = [os.path.join(software_userdir,x) for x in 
                                    os.listdir(software_userdir) if 
                                    x.endswith('.yaml')]
        
        LOG.debug("Found resource config files: %s" % resource_config_files)
        LOG.debug("Found standard config files: %s" % config_files) 
        return (resource_config_files, config_files)
    
    def load_software_config(self, conf_file, resource=True):
        # Parse the specified config file into a dictionary
        if resource:
            conf = yaml.load(resource_string('deployer.config.software', conf_file))
        else:
            with open(conf_file, 'r') as f:
                conf = yaml.load(f.read())
        software_conf = conf['software']
        LOG.debug('Read configuration for software <%s>...' % software_conf['id'])
        return conf
    
    def read_software_config(self, sc):
        # Load the provided software config into an instance of the config class
        # Get the software name from the config and get a ref to the class obj
        LOG.debug('Reading config for software: %s' % sc['software']['id'])
        
        software_os = sc['software']['os_type']
        software_package_manager = sc['software']['package_manager']
        os_pm = software_os + '_' + software_package_manager
        
        cls = get_software_config_class(os_pm)
        if cls == None:
            raise TypeError('A configuration class is not available for '
                            'software using the <%s> '
                            'package manager' % os_pm)
        config = cls(sc['software']['id'], sc['software']['name'],  
                     sc['software']['os_type'], sc['software']['os_flavour'])
    
        # Now handle all the parameters that are specific to this type of class
        # To do this, we walk through the parameters from the YAML file, 
        # setting these on the configuration class. 
        property_list = self._get_config_properties(cls)
        
        LOG.debug('PROPERTY_LIST:\n\n%s' % property_list)
        
        # Now walk through the YAML, check if a property exists in 
        # the property_list - if a property exists, set it on the configuration
        # object.
        config_items = self._get_yaml_config_items(sc['software'])
        
        LOG.debug('CONFIG_ITEMS:\n\n%s' % config_items)
        
        # Before setting the parameters, 
        
        # Iterate through config items and see, for each of the classes in the 
        # config class hierarchy whether the key is in the class dictionary 
        # whether property in the class is the same type as the property we 
        # are testing here.
        for k, v in config_items.iteritems():
            if k in property_list and (k not in ['software_id', 'software_name', 
                                                 'software_os_type', 
                                                 'software_os_flavour']):
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
                LOG.warning('Ignoring software property <%s>' % k)
        
        return config
    
    def load_software_configs(self):
        # Load all platform configurations and store them as a class in the 
        # _software array.
        files = self.get_platform_config_files()
        for f in files:
            pc = self.load_platform_config(f)
            conf_obj = self.read_platform_config(pc)
            self._software[conf_obj.name] = conf_obj
    
    def get_software_names(self):
        return self._software.keys()
    
    def get_software_configuration(self, name):
        try:
            return self._software[name]
        except KeyError:
            raise ValueError('An app with the ID <%s> is not registered '
                             'with this configuration manager.' % name)

    
    def _get_config_properties(self, config_class):
        # Get the full set of configuration properties from the target 
        # configuration class.
        # Check we received a class instance
        if not inspect.isclass(config_class):
            raise TypeError('This function must be called with a SoftwareConfig'
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
                    items[new_key] = v
        get_values(yaml_obj, 'software')
        return items
        
    
class SoftwareConfig(object):
    _software_id = None
    _software_name = None
    _software_os_type = None
    _software_os_flavour = None
    #_software_package_manager = None

    def __init__(self, sid, sname, s_os, s_osflavour):
        self._software_id = sid
        self._software_name = sname
        self._software_os_type = s_os
        self._software_os_flavour = s_osflavour
        
    @property
    def software_id(self):
        return self._software_id
    
    @property
    def software_name(self):
        return self._software_name
    
    @property
    def software_os_type(self):
        return self._software_os_type
    
    @property
    def software_os_flavour(self):
        return self._software_os_flavour
    
    # To be overriden by subclasses
    def get_install_commands(self):
        return []
    
    def get_info(self):
        conf_str = ('ID:\t\t%s\nName:\t\t%s\nOS Type:\t%s\n'
                    'OS Flavour:\t%s' 
                    % (self._software_id, self._software_name, 
                       self._software_os_type, self._software_os_flavour))
        return conf_str
    
    def print_info(self):
        conf_str = self.get_info()
        LOG.debug('\nSOFTWARE BASE CONFIG INFO:\n'
                  '--------------------------\n%s' % conf_str)
        
# Main function for testing
if __name__ == '__main__':
    cfg_man = SoftwareConfigManager.get_instance()
    
    # Init configuration handles all of the above functionality 
    cfg_man.init_configuration()
     
    software_names = cfg_man.get_software_names()
    print "Registered software: \n"
    for n in software_names:
        print "\tSoftware: %s" % n
    print '\n\n'
     
    for n in software_names:
        pc = cfg_man.get_software_configuration(n)
        pinfo = pc.get_info()
        print "Info for software <%s>:\n\n%s\n\n" % (n, pinfo)

class SoftwareConfigFile(object):
    '''
    Class representing a string of file data to be written to a remote
    file as part of the software configuration process.
    '''
    
    _data = None
    _filename = None
    
    def __init__(self, data, filename):
        self._data = data
        self._filename = filename
        
    @property
    def data(self):
        return self._data
    
    @property
    def filename(self):
        return self._filename
    
    def __str__(self, *args, **kwargs):
        return ('SoftwareConfigFile - WRITE DATA %s... TO REMOTE FILE %s'
                % (self._data[0:10], self._filename))
