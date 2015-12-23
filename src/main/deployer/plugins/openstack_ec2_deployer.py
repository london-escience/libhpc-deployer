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

OpenStack EC2 deployer. Uses the Eucalpytus provider to provide access
to the EC2 interface of an OpenStack deployment.
'''
import logging
import os
import socket
import tempfile
import time
from math import ceil

from deployer.config.software.base import SoftwareConfigManager,\
    SoftwareConfigFile
from deployer.core.deployment_interface import JobDeploymentBase
from deployer.core.exceptions import ResourceInitialisationError, JobError,\
    InvalidCredentialsError
from deployer.core.utils import generate_instance_id

from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider
from libcloud.security import VERIFY_SSL_CERT

import saga.job
from saga.exceptions import NoSuccess, BadParameter, AuthenticationFailed
from saga.filesystem import Directory, File
from saga.utils.pty_shell import PTYShell

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M')
logging.getLogger(__name__).setLevel(logging.DEBUG)

class JobDeploymentEC2Openstack(JobDeploymentBase):
    '''
    This is a deployer implementation for deploying code and running jobs on 
    OpenStack cloud resources via the EC2 interface. It uses the Eucalyptus 
    provider within libcloud to support this functionality.
    
    The workflow of deployment and job execution used here covers all the 
    stages set out in the base deployer class so all functions from the base 
    class are overloaded.  
    '''
    
    # The libcloud driver for OpenStack, configured in the constructor
    driver = None

    def __init__(self, platform_config):
        '''
        Constructor
        '''
        super(JobDeploymentEC2Openstack, self).__init__(platform_config)
        
        # Here we set up Apache libcloud with the necessary config obtained
        # from the job config
        # Prepare the necessary config information from the job config object.
        host = self.platform_config.platform_service_host
        port = self.platform_config.platform_service_port
        
        access_key = self.platform_config.access_key
        secret_key = self.platform_config.secret_key
        #region = self.platform_config.service_region
        
        VERIFY_SSL_CERT = False

        EUCA = get_driver(Provider.EUCALYPTUS) 
        self.driver = EUCA(access_key, secret=secret_key, secure=False, 
                          host=host, port=port, path='/services/Cloud')
        
        LOG.debug('The cloud driver instance is <%s>' % self.driver)
        
        # SAGA Session is pre-created by superclass
        # Prepare the job security context and store it - this will allow
        # access to the node(s) for running the job.
        # We add this to the session if/when required.
        self.job_ctx = saga.Context("ssh")
        self.job_ctx.user_id = self.platform_config.user_id
        self.job_ctx.user_key = self.platform_config.user_key_file
        self.admin_ctx = None
        LOG.debug('Set up security context for job account...')
                
    def initialise_resources(self, prefer_unconfigured=True, 
                             num_processes=1, processes_per_node=1,
                             node_type='m1.small', job_id=None, retries=3,
                             software_config=None):
        JobDeploymentBase.initialise_resources(self)
        # Start up the cloud resources here and wait for them to reach the 
        # running state. Need to know the image ID that we're starting. The
        # image ID is available from the job configuration
        image_id = None
        image_preconfigured_id = self.platform_config.image_preconfigured_id
        image_unconfigured_id = self.platform_config.image_unconfigured_id
        
        # Store whether or not we're using an unconfigured image - this 
        # determines whether we end up running the deploy software function
        # or not.
        self.use_unconfigured = False
        if image_preconfigured_id and not image_unconfigured_id:
            image_id = image_preconfigured_id
            LOG.debug('Only a configured image identifier has been provided, '
                      'using image ID <%s>.' % image_id)
        elif (not image_preconfigured_id) and image_unconfigured_id:
            image_id = image_unconfigured_id
            self.use_unconfigured = True
            LOG.debug('Only an unconfigured image identifier has been '
                      'provided, using image ID <%s>.' % image_id)
            if not software_config:
                raise JobError('Only an unconfigured image identifier has been '
                      'provided but no software config has been specified. '
                      'Unable to continue...')
        elif image_preconfigured_id and image_unconfigured_id:
            LOG.debug('Both configured and unconfigured images provided...')
            if prefer_unconfigured:
                image_id = image_unconfigured_id
                self.use_unconfigured = True
                LOG.debug('Using unconfigured image ID <%s>.' % image_id)
                if not software_config:
                    raise JobError('An unconfigured image identifier has been '
                          'chosen but no software config has been specified. '
                          'Unable to continue...')
            else:
                image_id = image_preconfigured_id
                LOG.debug('Using pre-configured image ID <%s>.' % image_id)            
        else:
            raise ResourceInitialisationError('ERROR: No image information '
                             'available in the platform configuration, unable '
                             'to initialise resources.')
            
        # If we're using an unconfigured image, we need to prepare the admin
        # security context based on the information that should be provided
        # in the YAML file with the unconfigured image details.
        if self.use_unconfigured:
            self.admin_ctx = saga.Context("ssh")
            self.admin_ctx.user_id = self.platform_config.image_unconfigured_admin_key_user
            self.admin_ctx.user_key = self.platform_config.image_unconfigured_admin_key_file
            
        # Check that the image is present and then use the libcloud driver to  
        # start the resources and return once they're running. 
        # TODO: This is currently synchronous but could also be done  
        # asynchronously using a callback to notify the caller when the nodes 
        # are ready. 
        
        #images = self.driver.list_images()
        #img = next((i for i in images if i.id == image_id), None)
        #if not img:
        
        img = None
        try:
            #img = self.driver.get_image(image_id)
            images = self.driver.list_images()
            for image in images:
                if image.id == image_id:
                    img = image
                    break
            if img == None:
                raise ResourceInitialisationError('The specified image <%s> '
                                                  'could not be found' % image_id)
        except socket.error as e:
            img = None
            raise ResourceInitialisationError('ERROR contacting the remote '
                             'cloud platform. Do you have an active network '
                             'connection? - <%s>' % str(e))
        except Exception as e:
            LOG.debug('ERROR STRING: %s' % str(e))
            img = None
            if str(e).startswith('Unauthorized:'):
                raise InvalidCredentialsError('ERROR: Access to the cloud '
                             'platform at <%s> was not authorised. Are your '
                             'credentials correct?' % 
                             (self.platform_config.platform_service_host + ':' 
                              + str(self.platform_config.platform_service_port)))
            else:
                raise ResourceInitialisationError('ERROR: The specified image <%s> '
                             'is not present on the target platform, unable '
                             'to start resources.' % image_id)
        
        sizes = self.driver.list_sizes()
        size = next((s for s in sizes if s.id == node_type), None)
        if not size:
            raise ResourceInitialisationError('ERROR: The specified resource '
                             'size (node_type) <%s> is not present on the '
                             'target platform. Unable to start resources. Have '
                             'you set the node_type parameter in your job spec?'
                              % node_type)
        
        # Get the keypair name from the configuration
        # If we're using an unconfigured resource, we use the admin key pair
        # name if provided. 
        if self.use_unconfigured and self.platform_config.image_unconfigured_admin_key_name:
            keypair_name = self.platform_config.image_unconfigured_admin_key_name
        else:
            keypair_name = self.platform_config.user_key_name
        
        # Get the number of resources from the job configuration
        # TODO: Fix this to obtain number of cores per node from the cloud
        # cloud platform. For now use the specified processes_per_node in the 
        # job specification. 
        cores_per_node = processes_per_node
        #cores_per_node = self.RESOURCE_TYPE_CORES[node_type]
        #if cores_per_node < processes_per_node:
        #    LOG.debug('A processes_per_node value <%s> greater than the number '
        #              'of cores in a node <%s> has been specified. Altering '
        #              'processes per node to the maximum available on this '
        #              'node type <%s>.' % (processes_per_node, cores_per_node,
        #                                   node_type))
        #    processes_per_node = cores_per_node
        num_nodes = int(ceil(float(num_processes)/float(processes_per_node)))
        
        # At this point we know that the image is available and the specified 
        # resource type is valid so we can request to start the instance(s)
        LOG.debug('About to start <%s> resources of type <%s> based on image '
                  '<%s (%s)> with keypair <%s>.' % (num_nodes, size.name, 
                  img.id, img.name, keypair_name))
        
        # When starting a resource we need the name, image, type, keypair, 
        # configuration data and details of the number of resources to start.
        name = job_id
        if not name:
            name = generate_instance_id()
         
        self.nodes = self.driver.create_node(name=name, image=img, size=size,
                                        ex_keyname=keypair_name,
                                        ex_mincount=num_nodes,
                                        ex_maxcount=num_nodes)
        
        if type(self.nodes) != type([]):
            self.nodes = [self.nodes]
        
        self.running_nodes = self.driver.wait_until_running(self.nodes)
                
        # Before we return details of the running nodes, we need to check
        # that they're accessible - it takes some time for the nodes to boot
        # and become available. We do this by setting up a handle to a 
        # directory - we assume all nodes have a '/' directory - and then 
        # trying to list that directory. If an exception is thrown, we assume
        # that the nodes are not yet available.
        
        # TODO: Need to replace this wait with a reliable check as to whether 
        # the server is up and running. Looks like, for now, this will need to 
        # use Paramiko while awaiting updates on saga-python.
        #LOG.debug('Waiting 60 seconds for node to boot...')
        #time.sleep(60)
        # Replaced 60 second wait with check using Paramiko to see if 
        # resource is accessible...
        LOG.debug('Checking node is available...')
        
        nodes_to_check = []
        for node in self.running_nodes:
            nodes_to_check.append(node[0].public_ips[0])
            
        res = self._wait_for_node_accessbility(nodes_to_check, 
                                               self.platform_config.user_id, 
                                               self.platform_config.user_key_file,
                                               retries=retries)
        if not res:
            # We still have nodes that are not avialable so assume there's a 
            # problem and throw a job error.
            raise JobError('After <%s> retries, the following nodes are '
                           'still not accessible <%s>. Cancelling job.'
                           % (retries, nodes_to_check))
        
        # If we have multiple nodes, now is the time to create the machinefile
        # for MPI job runs
        # For the machinefile we need the private IP of each node and the 
        # number of cores.
        machinefile = tempfile.NamedTemporaryFile('w', delete=True)
        machinefile.write("# Machine file for MPI job runs\n")
        for node in self.running_nodes:
            machinefile.write('%s slots=%s max_slots=%s\n' 
                              % (node[0].private_ips[0],
                                 cores_per_node, cores_per_node))
        machinefile.flush()
        LOG.debug('The following machinefile has been created:\n\n%s\n' 
                  % machinefile.name)
        
        # The master node is always considered to be node 0 in 
        # the self.running_nodes list.
        LOG.debug('Copying machinefile to master node...')
        saga_machinefile = File('file://%s' % machinefile.name, session=self.session)
        saga_machinefile.copy('sftp://%s/tmp/machinefile' 
                              % self.running_nodes[0][0].public_ips[0])
        machinefile.close()
        LOG.debug('machinefile copied to master node...')
        
        conn = PTYShell('ssh://%s' % self.running_nodes[0][0].public_ips[0], 
                        session=self.session)
        conn.run_sync('chmod 644 /tmp/machinefile')
        LOG.debug('Set permissions on /tmp/machinefile on master node to 644.')
        
        return self.running_nodes

    def deploy_software(self, software_config = None):
        JobDeploymentBase.deploy_software(self)
        # Here we undertake transfer of the code to the remote platform if this 
        # is required. In many cases, the software is likely to already be 
        # deployed on the target platform or may have been configured via a 
        # tool such as cloud-init, puppet, etc at resource initialisation time.
        LOG.debug('Deploy software...')
        
        # If we're not using an unconfigured image, we don't need to run the 
        # deploy software function
        if not self.use_unconfigured:
            LOG.info('Using a pre-configured image so running software '
                      'deployment process...')
            return
        
        # Software deployment requires root access to the target node(s). This
        # should be possible using the key that has been passed to start the 
        # reosurce(s). 
        
        # If no software configuration is provided, we ignore this function
        # call and return. If a configuration is provided, we check that the
        # configuration is for the right type of platform and then deploy
        # the software.
        if not software_config:
            return
        
        if type(software_config) != type([]):
            software_config = [software_config]
        
        LOG.debug('Received a request to deploy the following software '
                  'configuration IDs to the target platforms: <%s>...'
                  % software_config)
        
        
        # Check that we have an admin security context available. If we don't
        # we can't connect to the remote resource(s) to do the required 
        # configuration
        if not self.admin_ctx:
            raise JobError('deploy_software: There is no admin context '
                           'available so it will not be possible to connect '
                           'to remote resources to configure them. Ensure that '
                           '') 
        
        # Check that we can get each of the software configurations and that 
        # each one supports the target deployment platform.
        scm = SoftwareConfigManager.get_instance()
        scm.init_configuration()
        
        os_name = self.platform_config.image_unconfigured_os
        flavour = self.platform_config.image_unconfigured_flavour
        admin_key_user = self.platform_config.image_unconfigured_admin_key_user
        admin_key_file = self.platform_config.image_unconfigured_admin_key_file
        
        sc_dict = {}
        for sc in software_config:
            try:
                conf = scm.get_software_configuration(sc)
                sc_dict[sc] = conf
            except ValueError as e:
                raise JobError('Job error - no software could be found for '
                               'the configuration id <%s>: %s' % (sc, str(e)))
        
            if not ((os_name == conf.software_os_type) and
                    (flavour == conf.software_os_flavour)):
                LOG.error('The OS <%s> and flavour <%s> in the provided software '
                          'configuration don\'t match the target platform with '
                          'OS <%s> and flavour <%s>.' % 
                          (conf.software_os_type, 
                           conf.software_os_flavour, os_name, flavour))
                raise JobError('The OS <%s> and flavour <%s> in the provided '
                               'software configuration don\'t match the target '
                               'platform with OS <%s> and flavour <%s>.' %
                               (conf.software_os_type,
                                conf.software_os_flavour, os_name, flavour))
            
        # If we reach this point we assume that each of the software 
        # configurations has been found and they are for the right target 
        # platform.
        for sc_key in sc_dict.keys():
            sc_obj = sc_dict[sc_key]
            install_commands = sc_obj.get_install_commands()
            
            # Now run each of the install commands synchronously on all of the
            # target machines to get the software installed.
            node_ips = [node[0].public_ips[0] for node in self.running_nodes]
            LOG.debug('Deploying to the following list of nodes: %s' % node_ips)
            
            # Set up a new session using the admin user and key provided for 
            # the unconfigured image.
            adm_session = saga.Session(default=False)
            adm_ctx = saga.Context("ssh")
            adm_ctx.user_id = admin_key_user
            adm_ctx.user_key = admin_key_file
            adm_session.add_context(adm_ctx)
            # Open shell connections to each of the machines
            shell_conns = []
            opts = {}
            opts['ssh_options'] = {'StrictHostKeyChecking':'no'}
            for node_ip in node_ips:
                conn = PTYShell('ssh://%s' % node_ip, session=adm_session,
                                opts=opts)
                shell_conns.append(conn)
                if conf.software_os_type == 'linux':
                    self._setup_job_account(conn, self.platform_config)
                else:
                    LOG.warning('Support for creation of job accounts on ' 
                        'platforms other than linux is not yet supported...')
            # Copy the job account key to the master node
            job_session = saga.Session(default=False)
            job_session.add_context(self.job_ctx)
            
            keyfile = File('file://%s' % self.platform_config.user_key_file,
                           session=job_session)
            keyfile_target = shell_conns[0].url + os.path.join( 
                                          self.platform_config.user_home,
                                          '.ssh','id_rsa')
            LOG.debug('Copying job key to target directory <%s>' % keyfile_target)
            keyfile.copy(keyfile_target)
            for cmd in install_commands:
                for shell_connection in shell_conns:
                    if isinstance(cmd, SoftwareConfigFile):
                        LOG.debug('Software deployment: About to write data to '
                                  'remote file <%s> on node <%s>'
                                  % (cmd.filename, shell_connection.url)) 
                        shell_connection.write_to_remote(cmd.data, cmd.filename)
                    else:
                        LOG.debug('Software deployment: About to run command '
                                  '<%s> on resource <%s>...' 
                                  % (cmd, shell_connection.url))
                        if admin_key_user != 'root':
                            cmd = 'sudo ' + cmd
                        result, out, err = shell_connection.run_sync(cmd)
                        LOG.debug('Command completed - Exit code: <%s>, '
                                  'StdOut: <%s>, StdErr:\n<%s>'
                                  % (result, out, err))
    

    def transfer_files(self):
        JobDeploymentBase.transfer_files(self)
        # Here we transfer any input files to the relevant directory on the 
        # target platform. 
        # Use SAGA-Python to handle the file transfer.
        LOG.debug('Transfer files...')
        job_dir = self.platform_config.storage_job_directory
        
        # At this point we need to switch back to using the job secruity 
        # context. If we were using unconfigured resources, these will have
        # been configured using an admin context by now.
        self.session = saga.Session(default = False)
        self.session.add_context(self.job_ctx)
        
        # Begin by checking if we're working with more than one instance, if
        # so we have a master and one or more slave nodes. We'll push the data 
        # to the master and then direct the master to distribute it to the 
        # slave nodes.
        master_node = self.running_nodes[0][0]
        slave_nodes = []
        if len(self.running_nodes) > 1:
            slave_nodes = [node[0] for node in self.running_nodes[1:]]
        
        # On the master node: Check that the job storage directory exists and  
        # then create a sub-directory specifically for this job.
        
        # Node is a tuple consisting of two items, the node object and an 
        # IP list. For now we work with the node object directly. 
        node_ip = master_node.public_ips[0]
        try:
            directory = Directory('sftp://%s%s' % (node_ip, job_dir), session=self.session)
        except saga.BadParameter as e:
            LOG.error('The specified job directory does not exist on node '
                      '<%s> (%s).' % (node_ip, str(e)))
            #raise JobError('The specified job directory does not exist '
            #               'on node <%s> (%s)' % (node_ip, str(e)))
        try:
            # directory.make_dir() does not return a handle to the new directory
            # so need to create the directory URL manually.
            directory.make_dir(self.job_config.job_id)  
        except saga.NoSuccess as e:
            LOG.warning('The specified job data directory already exists on '
                      'node <%s> (%s).' % (node_ip, str(e)))
            #raise JobError('The specified job directory already exists on '
            #               'on node <%s> (%s)' % (node_ip, str(e)))
        
        job_data_dir = os.path.join(str(directory.url),self.job_config.job_id)
        
        # Now upload the file(s) to the job data directory
        # and create an input file list containing the resulting locations
        # of the files.
        # There are some cases where jobs may not have input files (they may, 
        # for example pull the input files from a remote location as part of 
        # the job process) so we first check whether there are any input files
        # to process, if not, then return from this function
        if not self.job_config.input_files:
            LOG.debug('There are no input files to transfer for this job...')
            return
        
        self.transferred_input_files = []
        for f in self.job_config.input_files:
            try:
                f_obj = File('file://%s' % f, session=self.session)
                f_obj.copy(job_data_dir)
                dest_dir = os.path.join(directory.url.path,self.job_config.job_id)
                self.transferred_input_files.append(
                    os.path.join(dest_dir, 
                    os.path.basename(f_obj.url.path)))
            except:
                LOG.error('Error copying the input file <%s> to the remote '
                          'platform.' % f)
                raise JobError('Error copying the input file <%s> to the '
                               'remote platform.' % f)
        
        # At this point input files have been successfully transferred to 
        # the master node. We now direct the master node to send the files 
        # to each of the slave nodes:
        if slave_nodes:
            slave_private_ips = [node.private_ips[0] for node in slave_nodes]
            self._distribute_job_data(master_node.public_ips[0], 
                                      slave_private_ips, 
                                      self.platform_config.user_id, 
                                      self.platform_config.user_key_file, 
                                      job_dir, self.job_config.job_id)

    def run_job(self):
        JobDeploymentBase.run_job(self)
        # This function uses the libhpc resource daemon client to talk to the 
        # resource daemon that is installed on cloud resources. It uses this 
        # interface to run jobs and monitor their state to see when they are 
        # complete.
        # TODO: Should this be running/managing the job remotely via a SAGA
        # SSH session or should we be expecting to communicate with a remote 
        # resource management service to handle this?
        LOG.debug('Run job...')
        
        job_arguments = getattr(self.job_config, 'args', [])
        input_files = getattr(self, 'transferred_input_files', [])
        job_arguments += input_files
        
        # Check if we have a JOB_ID variable in the arguments or input files.
        # If so, replace this variable with the actual job ID.
        job_arguments_tmp = job_arguments
        job_arguments = []
        for item in job_arguments_tmp:
            # Can't do a replace on items that are not string types!
            if isinstance(item, basestring):
                job_arguments.append(item.replace('$JOB_ID', self.job_config.job_id))
            else:
                job_arguments.append(item)
        
        LOG.debug('Modified job arguments: %s' % job_arguments)
        
        jd = saga.job.Description()
        jd.environment = getattr(self.job_config, 'environment', {})
        if self.job_config.num_processes > 1:
            jd.executable  = ('mpirun -np %s -machinefile /tmp/machinefile'
                              % (self.job_config.num_processes))
            executable = getattr(self.job_config, 'executable', None)
            if executable:
                job_arguments.insert(0, executable)
        else:
            jd.executable  = getattr(self.job_config, 'executable', None)
        jd.arguments   = job_arguments
        jd.working_directory = getattr(self.job_config, 'working_dir', None)
        jd.output      = getattr(self.job_config, 'stdout', None)
        jd.error       = getattr(self.job_config, 'stderr', None)
        jd.wall_time_limit = getattr(self.job_config, 'time_limit_mins', 0)
        #jd.number_of_processes = 4
        #jd.processes_per_host = 1
        #jd.total_physical_memory = "2400"
        
        if not jd.output:
            jd.output = 'std.out'
        if not jd.error:
            jd.error = 'std.err'
        
        self.svc = saga.job.Service('ssh://%s/' % self.running_nodes[0][0].public_ips[0], session=self.session)
        self.job = self.svc.create_job(jd)
        self.job.run()
        
    def wait_for_job_completion(self):
        LOG.debug('Waiting for job completion...')
        self.job.wait()
        LOG.debug('Job has finished...')
        return (None, None)

    def collect_output(self, destination):
        # Before calling the base implementation of output file collection to 
        # pull files back from the master node, we first need to gather output 
        # from each of the slave nodes onto the master node
        LOG.debug('Gather files from slave nodes to master...')
        job_dir = self.platform_config.storage_job_directory
        
        # If we have only one node then we can skip this stage...
        master_node = self.running_nodes[0][0]
        slave_nodes = []
        if len(self.running_nodes) > 1:
            slave_nodes = [node[0] for node in self.running_nodes[1:]]
        
        if slave_nodes:
            slave_private_ips = [node.private_ips[0] for node in slave_nodes]
            self._gather_results_data(master_node.public_ips[0], 
                                      slave_private_ips, 
                                      self.platform_config.user_id, 
                                      self.platform_config.user_key_file, 
                                      job_dir, self.job_config.job_id)
        
        # Using the base implementation of job output file collection...
        JobDeploymentBase.collect_output(self, destination)
        
        
    def shutdown_resources(self):
        JobDeploymentBase.shutdown_resources(self)
        # Here we terminate the running resources for this job and 
        # wait until they have been shut down.
        res_ids = [node.id for node in self.nodes]
        LOG.debug('About to shut down the following nodes: %s' % res_ids)
        
        LOG.debug('Shutdown resources...')
        for node in self.nodes:
            self.driver.destroy_node(node)
        
        while res_ids:
            nodes_to_wait_for = self.driver.list_nodes(res_ids)
            still_running = [node.id for node in nodes_to_wait_for]
            new_res_ids = []
            # Now go through res_ids and delete the nodes that don't appear
            # in still_running.
            for res_id in res_ids:
                if res_id not in still_running:
                    LOG.debug('Resource <%s> has terminated...' % res_id)
                else:
                    new_res_ids.append(res_id)
            res_ids = new_res_ids
            if res_ids:
                LOG.debug('Still waiting for termination of resources %s...'
                          % res_ids)
                time.sleep(2)
        
        LOG.debug('All resources terminated.')

    # This abstraction previously allowed easy switching between the saga and
    # paramiko implementations of this function. For now, the paramiko version
    # has been removed to remove the dependency on paramiko.
    def _wait_for_node_accessbility(self, *args, **kwargs):
        return self._wait_for_node_accessbility_saga(*args, **kwargs)

    def _wait_for_node_accessbility_saga(self, node_ip_list, user_id, key_file, 
                                    port=22, retries=3, pre_check_delay=10):
        # Using saga to check if remote resources are accessible
        #retries = 3
        retries = 5
        attempts_made = 0
        connection_successful = False
        
        LOG.debug('Waiting <%s> seconds to check for resource accessibility.'
                  % (pre_check_delay))
        time.sleep(pre_check_delay)
        
        # Create an empty session with no contexts
        self.session = saga.Session(default = False)
        if self.admin_ctx:
            self.session.add_context(self.admin_ctx)
        else:
            self.session.add_context(self.job_ctx)

        # TODO: Shouldn't try other security contexts until we've tried one 
        # context with all nodes, at present the connection fails because we 
        # switch contexts before checking each node...
        while attempts_made < retries and not connection_successful:
            nodes_ok = []
            for ip in node_ip_list:
                try:
                    LOG.debug('Attempt <%s> to connect to remote resource '
                              '<%s> using SAGA...' % (attempts_made+1, ip))
                    dir_obj = Directory('sftp://%s/' % ip, 
                                        session=self.session)
                    LOG.debug('Triggering connection to remote node by '
                              'attempting root dir list...')
                    dir_obj.list()
                    LOG.debug('Connected to remote node successfully...')
                    dir_obj.close()
                    LOG.debug('Closed connection to remote node...')
                    nodes_ok.append(ip)
                except socket.timeout:
                    LOG.debug('Timed out trying to connect to <%s>...'
                              % ip)
                except OSError as e:
                    LOG.debug('OSError trying to connect to <%s>: %s' % (ip, str(e)))
                except NoSuccess as e:
                    LOG.debug('NoSuccess making connection to resource <%s>: %s'
                              % (ip, str(e)))
                except BadParameter as e:
                    LOG.debug('BadParameter making connection to resource <%s>'
                              ': %s' % (ip, str(e)))
                except AuthenticationFailed as e:
                    LOG.debug('Authentication failure when making connection '
                              'to resource <%s>: %s\nTrying next security '
                              'context...' % (ip, str(e)))
                    raise NoSuccess('No valid security context for '
                                        'connection to resource <%s>.' % ip)
            
            node_ip_list = [item for item in node_ip_list if item not in nodes_ok]
            # if node list is empty and all nodes are running set flag to true
            if not node_ip_list:
                connection_successful = True
            attempts_made += 1
            
            if not connection_successful and attempts_made < retries: 
                wait_time = 10*attempts_made
                LOG.debug('Waiting <%s> seconds before retrying connection...' 
                          % wait_time)
                time.sleep(wait_time)
        
        if not connection_successful:
            LOG.debug('ERROR: Unable to connect to remote node...')
        else:
            LOG.debug('**** SAGA CONNECTION TO REMOTE NODE(S) SUCCESSFUL ****')
        
        return connection_successful
    
    def _distribute_job_data(self, master_ip, target_node_ip_list, 
                             user_id, key_file, remote_job_dir, job_id, 
                             port=22):
        
        if not target_node_ip_list:
            LOG.debug('No slave nodes to transfer data to...')
            return
        
        # Set up SAGA shell object for access to the remote resources
        if not hasattr(self,'shell'):
            self.shell = PTYShell('ssh://%s@%s/' % 
                                  (user_id, master_ip), session=self.session)
        
        # Execute command(s) on the remote master node to transfer data to 
        # slave nodes. 
        command_template = 'scp -o StrictHostKeyChecking=no -rp %s %s:%s/'
        # Now trigger the scp command to push data to each of the nodes
        for target_ip in target_node_ip_list:
            LOG.debug('About to transfer job files from master node to '
                      'remote node <%s>' % target_ip)
            command_to_run = command_template % (os.path.join(remote_job_dir, job_id),
                                           target_ip, remote_job_dir)
            LOG.debug('Command to run %s' % command_to_run)
            ret, out, err = self.shell.run_sync(command_to_run)
            
            LOG.debug('Command has run with return value <%s>\nstdout:\n<%s>'
                      '\nstderr: <%s>\n\n' % (ret, out, err))
            
            if ret != 0:
                raise JobError('Unable to distribute job data to remote node '
                               '<%s>, scp return value <%s>' % (target_ip, ret))
                
                
    def _gather_results_data(self, master_ip, target_node_ip_list, 
                     user_id, key_file, remote_job_dir, job_id, 
                     port=22):
        
        if not target_node_ip_list:
            LOG.debug('No slave nodes to gather data from...')
            return
        
        # Set up SAGA shell object for access to the remote resources
        if not hasattr(self,'shell'):
            self.shell = PTYShell('ssh://%s@%s/' % 
                                  (user_id, master_ip), session=self.session)
        
        # Execute command(s) on the remote master node to transfer data to 
        # slave nodes. 
        command_template = 'scp -rp %s:%s/* %s/'
        # Now trigger the scp command to push data to each of the nodes
        for target_ip in target_node_ip_list:
            LOG.debug('About to transfer job files from master node to '
                      'remote node <%s>' % target_ip)
            command_to_run = command_template % (target_ip, 
                                                 os.path.join(remote_job_dir, job_id),
                                                 os.path.join(remote_job_dir, job_id))
            LOG.debug('Command to run %s' % command_to_run)
            ret, out, err = self.shell.run_sync(command_to_run)
            
            LOG.debug('Gather command has run with return value <%s>\nstdout:'
                      '\n<%s>\nstderr: <%s>\n\n' % (ret, out, err))
            
            if ret != 0:
                raise JobError('Unable to gather job data from remote node '
                               '<%s>, scp return value <%s>' % (target_ip, ret))
                
    def _setup_job_account(self, pty_conn, platform_config):
        user_id = platform_config.user_id
        user_home = platform_config.user_home
        public_key = platform_config.user_public_key
        admin_user = platform_config.image_unconfigured_admin_key_user
        
        # Creating the job user on the remote node
        LOG.debug('Creating job user account for user <%s> on remote node <%s>'
                  % (user_id, pty_conn.url))
        # First check if the user directory exists
        cmd = 'sudo test -d %s'
        result, out, err = pty_conn.run_sync(cmd % (user_home))
        if result != 1:
            raise JobError('The specified user home directory <%s> for the job '
                           'user <%s> already exists. Unable to proceed with '
                           'resource configuration.' % (user_home, user_id))
        cmd = 'useradd -d %s -m %s'
        if admin_user != 'root':
            cmd = 'sudo ' + cmd
        result, out, err = pty_conn.run_sync(cmd % (user_home, user_id))
        LOG.debug('useradd command completed - Exit code: <%s>, '
                  'StdOut: <%s>, StdErr:\n<%s>'
                  % (result, out, err))
        
        # Check if user home created during user account creation
        # If account already existed, we may need to create the directory here
        try:
            home_dir = Directory(pty_conn.url + user_home, session=pty_conn.session)
        except BadParameter:
            # Assume home directory doesn't exist and create it here.
            rootdir = Directory(pty_conn.url + '/', session=pty_conn.session)
            rootdir.make_dir(user_home)
            home_dir = Directory(pty_conn.url + user_home, session=pty_conn.session)
            
        try:
            home_dir.make_dir(os.path.join(user_home,'.ssh'))
        except saga.NoSuccess as e:
            if 'exists' in str(e):
                LOG.debug('Directory <%s> already exists...' 
                          % os.path.join(user_home,'.ssh'))
            else:
                raise JobError('Unable to create the SSH directory in user '
                               'home <%s>...' % os.path.join(user_home,'.ssh'))
        
        try:
            home_dir.make_dir(platform_config.storage_job_directory)
        except saga.NoSuccess as e:
            if 'exists' in str(e):
                LOG.debug('Job data directory <%s> already exists...' 
                          % platform_config.storage_job_directory)
            else:
                raise JobError('Unable to create platform data directory '
                               '<%s>.' % platform_config.storage_job_directory)
        
        # Write the public key to the authorized keys file on the remote node
        pty_conn.write_to_remote(public_key, 
                                 os.path.join(user_home,'.ssh','authorized_keys'))
        
        # Change ownership of all created directories/files to the job user
        pty_conn.run_sync('chown -R %s:%s %s' % (user_id,user_id,user_home))
                
                        
