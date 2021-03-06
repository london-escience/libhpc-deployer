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
Created on 28 Jul 2015

@author: jcohen02
'''
import unittest
from mock.mock import Mock

from deployer.config.platform.base import DeployerConfigManager
from deployer.config.platform.openstack import OpenStackPlatformConfig
from deployer.config.platform.pbs import PBSProPlatformConfig

class GetValidPlatformConfigClassTestCase(unittest.TestCase):

    # Check that we're prevented from creating an instance of this class 
    # directly via its constructor. It is necessary to use get_instance 
    def test_get_platform_configuration_valid(self):
        mock_config_class = Mock(spec=OpenStackPlatformConfig)
        
        dcm = DeployerConfigManager.get_instance()
        # Inject the mocked platform config, with the correct key, into the 
        # config manager's list of platforms.
        dcm._software['openstack'] = mock_config_class
        c = dcm.get_platform_configuration('openstack')
        self.assertTrue(isinstance(c, OpenStackPlatformConfig))
        
class GetInvalidPlatformConfigClassTestCase(unittest.TestCase):
     
    def test_get_pbs_config_class(self):
        mock_config_class = Mock(spec=PBSProPlatformConfig)
        
        dcm = DeployerConfigManager.get_instance()
        dcm._software['pbspro'] = mock_config_class
        
        self.assertRaises(ValueError, dcm.get_platform_configuration,'openstack')

if __name__ == "__main__":
    unittest.main()
