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
#import os
#os.environ['SAGA_VERBOSE'] = 'DEBUG'

import logging
import importlib
from deployer.config.platform.base import DeployerConfigManager, PlatformConfig

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

DEPLOYER_CLASSES = {
    'PBS_PRO': ('deployer.pbs_deployer', 'JobDeploymentPBS'),
    'OPENSTACK': ('deployer.openstack_deployer', 'JobDeploymentOpenstack'),
    'OPENSTACK_EC2': ('deployer.openstack_ec2_deployer', 
                      'JobDeploymentEC2Openstack'),
    'EC2': ('deployer.ec2_deployer', 'JobDeploymentEC2'),
    'SSH_FORK': ('deployer.ssh_deployer', 'JobDeploymentSSH'),
}

class JobDeploymentFactory(object):
    '''
    The deployment factory will return a deployer suitable for the provided 
    platform configuration object.
    '''

    def __init__(self):
        '''
        Initialise a configuration manager that will be used to provide
        the configurations based on which deployer instances are created.  
        '''
        self.dcm = DeployerConfigManager.get_instance()
        self.dcm.init_configuration()
        
    def get_configuration_names(self):
        '''
        Get a list of names of the configurations based on which deployers
        can be generated.
        '''
        return self.dcm.get_platform_names()
    
    def get_deployer(self, config_id_or_obj):
        '''
        Based on the type of the stored configuration object, generate an 
        instance of the relevant deployment object and return it.
        
        config_id_or_object can be an instance of a configuration object or it  
        can be the ID of a registered job configuration.
        '''
        platform_config = None
        if type(config_id_or_obj) == type(''):
            platform_config = self.dcm.get_platform_configuration(config_id_or_obj)
        elif isinstance(config_id_or_obj, PlatformConfig):
            platform_config = config_id_or_obj
        else:
            raise ValueError('The provided config object is not a string ' 
                             'identifier or an instance of a PlatformConfig'
                             'object.')
                
        ptype = platform_config.platform_type
        
        try:
            dep_pkg, dep_cls = DEPLOYER_CLASSES[ptype.upper()]
        except KeyError:
            LOG.error('Unable to find a deployer implementation for platform '
                      'type <%s>.' % ptype.upper())
            return None
        
        try:
            mod = importlib.import_module(dep_pkg)
            cls = getattr(mod, dep_cls)
        except ImportError:
            LOG.error('Unable to load the module <%s> specified for the '
                      'deployer class <%s>.' % (dep_pkg, dep_cls))
            return None
        except AttributeError:
            LOG.error('Unable to load the deployer class <%s> in the specified '
                      'configuration package <%s>.' % (dep_cls, dep_pkg))
            return None
        
        deployer = cls(platform_config)
        return deployer