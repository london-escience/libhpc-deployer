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

import importlib
import logging

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

__all__ = [
    'PLATFORM_CONFIGS',
    'SOFTWARE_CONFIGS',
    'get_platform_config_class',
    'get_software_config',
]

PLATFORM_CONFIGS = {
    'OPENSTACK': ('deployer.config.platform.openstack','OpenStackPlatformConfig'),
    'OPENSTACK_EC2': ('deployer.config.platform.ec2','EC2PlatformConfig'),
    'EC2': ('deployer.config.platform.ec2','EC2PlatformConfig'),
    'PBS_PRO': ('deployer.config.platform.pbs','PBSProPlatformConfig'),
    'SSH_FORK': ('deployer.config.platform.ssh','SSHPlatformConfig'),
}

SOFTWARE_CONFIGS = {
    'LINUX_APT': ('deployer.config.software.linux','LinuxAPTConfig'),
}

def get_platform_config_class(platform):
    try:
        platform = platform.upper()
        config_package, config_class = PLATFORM_CONFIGS[platform]
    except KeyError:
        LOG.error('No configuration can be found for a platform with '
                  'name: <%s>' % platform)
        return None
    
    try:
        mod = importlib.import_module(config_package)
        cls = getattr(mod, config_class)
    except ImportError:
        LOG.error('Error loading the module <%s> specified for the '
                  'configuration class <%s>.' % (config_package, config_class))
        return None
    except AttributeError:
        LOG.error('Error loading the class <%s> within the configuration '
                  'package <%s>.' % (config_class, config_package))
        return None
    
    return cls

# Takes a string defining the operating system and package manager
# to obtain a software configuration class from.
def get_software_config_class(os_pm):
    try:
        os_pm_id = os_pm.upper()
        config_package, config_class = SOFTWARE_CONFIGS[os_pm_id]
    except KeyError:
        LOG.error('No configuration can be found for a s with '
                  'name: <%s>' % os_pm)
        return None
    
    try:
        mod = importlib.import_module(config_package)
        cls = getattr(mod, config_class)
    except ImportError:
        LOG.error('Error loading the module <%s> specified for the '
                  'configuration class <%s>.' % (config_package, config_class))
        return None
    except AttributeError:
        LOG.error('Error loading the class <%s> within the configuration '
                  'package <%s>.' % (config_class, config_package))
        return None
    
    return cls
        
