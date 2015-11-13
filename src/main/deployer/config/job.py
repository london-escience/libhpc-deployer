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
Created on 10 Aug 2015

@author: jcohen02

A job configuration class for representing the details of a job to be run 
by the deployer library.
'''
import os
import logging
import yaml
from deployer.utils import generate_job_id
from deployer.exceptions import JobConfigurationError

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class JobConfiguration(object):
    '''
    Job configuration class representing the complete configuration for a job. 
    '''

    _job_id = None
    _executable = None
    _node_type = None
    _input_files = []
    _args = []
    _num_processes = 1
    _processes_per_node = 1
    _working_dir = None
    _stdout = None
    _stderr = None
    
    # Where to copy the output files to.
    _output_file_destination = None
    
    # Whether to delete job data on the execution node after a job has finished
    _delete_job_files = False

    def __init__(self):
        '''
        Create a job identifier for this configuration.
        '''
        self._job_id = generate_job_id()
        LOG.debug('Generated a job ID for this job info <%s>...' % self._job_id)
        
    
    @property
    def job_id(self):
        return self._job_id
    
    @job_id.setter
    def job_id(self, value):
        self._job_id = value
    
    @property
    def executable(self):
        return self._executable
    
    @executable.setter
    def executable(self, value):
        self._executable = value
            
    @property
    def input_files(self):
        return self._input_files
    
    @input_files.setter
    def input_files(self, value_list):
        self._input_files = value_list

    @property
    def args(self):
        return self._args
    
    @args.setter
    def args(self, value):
        self._args = value
    
    @property
    def node_type(self):
        return self._node_type
    
    @node_type.setter
    def node_type(self, value):
        self._node_type = value

    @property
    def num_processes(self):
        return self._num_processes
    
    @num_processes.setter
    def num_processes(self, value):
        self._num_processes = value

    @property
    def processes_per_node(self):
        return self._processes_per_node
    
    @processes_per_node.setter
    def processes_per_node(self, value):
        self._processes_per_node = value
        
    @property
    def working_dir(self):
        return self._working_dir
    
    @working_dir.setter
    def working_dir(self, value):
        self._working_dir = value
        
    @property
    def stdout(self):
        return self._stdout
    
    @stdout.setter
    def stdout(self, value):
        self._stdout = value
        
    @property
    def stderr(self):
        return self._stderr
    
    @stderr.setter
    def stderr(self, value):
        self._stderr = value

    @property
    def output_file_destination(self):
        return self._output_file_destination
    
    @output_file_destination.setter
    def output_file_destination(self, value):
        self._output_file_destination = value
        
    @property
    def delete_job_files(self):
        return self._delete_job_files
    
    @delete_job_files.setter
    def delete_job_files(self, value):
        self._delete_job_files = value
    
    def get_info(self):
        conf_str = ('\nJob ID:\t\t\t\t%s\nInput files:\t\t\t%s\nArguments:'
                    '\t\t\t%s\nWorking directory:\t\t%s\n'
                    'Output file destination:\t%s\n\nNode type:\t\t\t%s\n'
                    'Number of processes:\t\t%s\nProcesses per node:\t\t%s\n'
                    'Delete job files:\t\t%s\n' 
                    % (self._job_id, self._input_files, self.args, 
                       self._working_dir, self._output_file_destination,  
                       self._node_type, self._num_processes,
                       self._processes_per_node, self._delete_job_files))
        return conf_str
    
    def print_info(self):
        conf_str = self.get_info()
        LOG.debug('\nBASE CONFIG INFO:\n----------------\n%s' % conf_str)

    # A static method to build a Job Configuration class instance from a 
    # provided YAMML file containing a job specification.
    @staticmethod
    def from_yaml(yaml_file):
        try:
            with open(yaml_file, 'r') as f:
                yaml_jobspec_data = f.read()
        except IOError as e:
            raise JobConfigurationError('Unable to read job specification: '
                                        '[%s]' % str(e))
        
        # Now create a new JobConfiguration and populate it with the values
        # from the YAML configuration.
        yaml_jobspec = yaml.load(yaml_jobspec_data)
        
        key_list = []
        if yaml_jobspec.keys()[0] != 'libhpc_jobspec':
            raise JobConfigurationError('The root key of a job specification '
                                        'must be "libhpc_jobspec"')
        jc = JobConfiguration()
        def dict_iter_items(d, base_key=''):
            for k,v in d.iteritems():
                key_list.append(k)
                if type(v) == dict:
                    if base_key == '':
                        base_key = k
                    else:
                        base_key = base_key + '_' + k 
                    dict_iter_items(v, base_key)
                else:
                    # Add the value to the job configuration object
                    jc.__class__.__dict__[k].__set__(jc, v)
        dict_iter_items(yaml_jobspec['libhpc_jobspec'])
        
        # Convert the output directory to an absolute path in case a relative
        # path was specified
        jc.output_file_destination = os.path.abspath(jc.output_file_destination)
        
        return jc
