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
Created on 6 Aug 2015

@author: jcohen02

Exceptions used in the deployer library
'''

class DeployerError(Exception):
    pass

class InvalidCredentialsError(DeployerError):
    pass

class ResourceInitialisationError(DeployerError):
    pass

class JobError(DeployerError):
    pass

class JobConfigurationError(DeployerError):
    pass

class ConnectionError(DeployerError):
    pass

class StorageDirectoryNotFoundError(DeployerError):
    pass

class DirectoryExistsError(DeployerError):
    pass
