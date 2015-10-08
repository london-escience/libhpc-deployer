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
Created on 7 Sep 2015

@author: jcohen02

Software configuration classes for different package managers in the linux 
system.

Currently provides an implementation only for Apt.
'''
import logging

from deployer.config.software.base import SoftwareConfig, SoftwareConfigFile

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class LinuxAPTConfig(SoftwareConfig):
    '''
    A software configuration class that extends the base software 
    configuration class and includes parameters for Linux platforms using the 
    apt package manager.
    '''
    
    def __init__(self, *args, **kwargs):
        super(LinuxAPTConfig, self).__init__(*args, **kwargs)
        
    # Linux/apt specific properties    
    _software_apt_config = []
    _software_packages = []
    
    #===========================================================================
    # PROPERTIES SPECIFIC TO Linux PLATFORMS USING THE APT PACKAGING TOOL
    #===========================================================================
    
    @property
    def software_apt_config(self):
        return self._software_apt_config
    
    @software_apt_config.setter
    def software_apt_config(self, value):
        if type(value) == type([]):
            for item in value:
                self._software_apt_config.append((item['source'], item['key']))
        
    @property
    def software_packages(self):
        return self._software_packages
    
    @software_packages.setter
    def software_packages(self, value):
        self._software_packages = value
        
    def get_install_commands(self):
        install_commands = []
        # Prepare commands to register all the keys and repositories in 
        # the provided apt config
        id = 0
        for item in self._software_apt_config:
            source = item[0]
            key = item[1]
            # Add the configuration to create the remote key file on the server
            remote_keyfile = '/tmp/pubkey' + str(id)
            file_config = SoftwareConfigFile(key, remote_keyfile)
            install_commands.append(file_config)
            
            # Add the configuration to create the remote sources.list entry
            remote_sources_file = ('/etc/apt/sources.list.d/%s%s.list'
                                   % (self._software_name, id))
            source_file_config = SoftwareConfigFile(source, remote_sources_file)
            install_commands.append(source_file_config)
            
            # Now set up the commands to register the key and update apt
            install_commands.append('cat %s | sudo apt-key add -; rm -f %s'
                                    % (remote_keyfile, remote_keyfile))
            install_commands.append('sudo apt-get update')
            
            id+=1
            
        # Now setup the command to install the software packages
        package_list = ' '.join(self._software_packages)
        install_commands.append('sudo apt-get install -y %s' % package_list)
        
        install_commands_str = [str(item) for item in install_commands]
               
        LOG.debug('COMMANDS TO RUN FOR CONFIGURATION:\n%s'
                  % '\n'.join(install_commands_str))
        
        return install_commands
    
    def get_info(self):
        base_info = SoftwareConfig.get_info(self)
        base_info += ('\n\nParameters specific to Linux/APT platforms:\n\n'
                      'Sources: \n')
        
        for source, key in self._software_apt_config:
            base_info += '\tSource:\t\t%s,\t\tKey:%s...' % (source, key[0:10])
        
        base_info += 'Packages:\n'
        
        for package in self._software_packages:
            base_info += '\tPackage: %s\n' % package
        
        return base_info
        
