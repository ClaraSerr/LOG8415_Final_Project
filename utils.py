def create_security_group(ec2_RESSOURCE, ec2_CLIENT, ClientError, Vpcid, ports):
    """
    Creates a security group with 3 inbound rules allowing TCP traffic through custom ports

    Parameters
    ----------
    Vpcid : str
        id of the vpc in use
    ports : list of int
        list of ports for which to add inbound and outbound rule

    Returns
    -------
    int
        id of the created security group

    Raises
    ------
    ClientError
        If the connection is not possible
    """
    # We will create a security group in the existing VPC
    try:
        security_group = ec2_RESSOURCE.create_security_group(GroupName='security_group',
                                             Description='Flask_Security_Group',
                                             VpcId=Vpcid,
                                             )
        security_group_id = security_group.group_id
        for port in ports: # In our use case, ports = [22, 80, 443, 1186, 3306]
            security_group.authorize_ingress(
                DryRun=False,
                IpPermissions=[
                    {
                        'FromPort': port,
                        'ToPort': port,
                        'IpProtocol': 'TCP',
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': "MySQL"
                            },
                        ]
                    }
                ]
            )
            ec2_CLIENT.authorize_security_group_egress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'FromPort': port,
                        'ToPort': port,
                        'IpProtocol': 'TCP',
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': "MySQL"
                            },
                        ]
                    }
                ]
            )
        # add ICMP-IPv4 inbound and outbound rule for all ports
        security_group.authorize_ingress(
                DryRun=False,
                IpPermissions=[
                    {
                        'FromPort': -1,
                        'ToPort': -1,
                        'IpProtocol': 'ICMP',
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': "MySQL"
                            },
                        ]
                    }
                ]
            )
        ec2_CLIENT.authorize_security_group_egress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'FromPort': -1,
                        'ToPort': -1,
                        'IpProtocol': 'ICMP',
                        'IpRanges': [
                            {
                                'CidrIp': '0.0.0.0/0',
                                'Description': "MySQL"
                            },
                        ]
                    }
                ]
            )
        print('Security Group Created %s in vpc %s.' %
              (security_group_id, Vpcid))
        return security_group_id
    except ClientError as e:
        print(e)

def create_instance(ec2_RESSOURCE, instance_type,keyname,name,security_id,availability_zone):
    """
    Creates an instance with specified parameters

    Parameters
    ----------
    instance_type : str
        type of the intance to launch
    keyname : str
        name of the key to use for the instance
    name : str
        name of the instance to launch
    security_id : str
        id of the security group to use for the launch
    availability_zone : str
        aailability zone to launch the instance

    Returns
    -------
    ec2.Instance
        The resources of the created instance
    """
    Instance=ec2_RESSOURCE.create_instances(
        ImageId="ami-08c40ec9ead489470",
        InstanceType=instance_type,
        KeyName=keyname,
        MinCount=1,
        MaxCount=1,
        # Specify the number of the instances in its Tag Name
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value':  name
                    },
                ]
            },
        ],
        SecurityGroupIds=[security_id],
        Placement={
            'AvailabilityZone': availability_zone})
    print(f"{name} instance created {Instance[0]}")
    return Instance[0]


def create_commands_stand_alone():
    """
    Creates a lists of the commands to run on the instances we connected into via paramiko

    Returns
    -------
    list
        list of the commands to run
    """
    
    commands = [
        'sudo apt-get update', 
        'yes | sudo apt-get upgrade',
        'yes | sudo apt-get install mysql-server',
        # install sysbench
        "yes | sudo apt-get install sysbench",

        # Download Sakila database
        'wget https://downloads.mysql.com/docs/sakila-db.tar.gz',

        # Unpack sakila
        'tar -xf sakila-db.tar.gz',

        # Remove compressed folder
        'rm sakila-db.tar.gz',

        # Import and use the sakila database
        'sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;"',
        'sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"',
        'sudo mysql -e "USE sakila;"'
    ]
    return commands

def create_commands_cluster():
    """
    Creates a lists of the commands to run on all instances of the cluster
    Follow the tutorial: https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        'sudo apt-get update',
        # install sysbench
        "yes | sudo apt-get install sysbench",

        'sudo mkdir -p /opt/mysqlcluster/home',
        # give root permissions to the whole folder
        'sudo chmod -R 777 /opt/mysqlcluster',

        # download MySQL and put it in the appropriate folder
        'wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz -P /opt/mysqlcluster/home/',
        'tar -xvf /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz -C /opt/mysqlcluster/home/',

        # create Symlink to the decompressed directory
        'ln -s /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64 /opt/mysqlcluster/home/mysqlc',
        'rm /opt/mysqlcluster/home/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',

        # export appropriate paths
        'sudo chmod -R 777 /etc/profile.d',
        'echo "export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc" > /etc/profile.d/mysqlc.sh',
        'echo "export PATH=$MYSQLC_HOME/bin:$PATH" >> /etc/profile.d/mysqlc.sh',
        'source /etc/profile.d/mysqlc.sh',
        'sudo apt-get update && sudo apt-get -y install libncurses5'
    ]

    return commands

def create_commands_cluster_master_1(DNS_private_addresses):
    """
    Creates a lists of the commands to run only on the master instance we connected into via paramiko
    Follow the tutorial: https://stansantiago.wordpress.com/2012/01/04/installing-mysql-cluster-on-ec2/

    Parameters
    ----------
    DNS_private_addresses : dict(str -> str)
        Values are the private DNS addresses of each instance. The key is the instance's name.

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        'mkdir -p /opt/mysqlcluster/deploy/conf',
        'mkdir -p /opt/mysqlcluster/deploy/mysqld_data',
        'mkdir -p /opt/mysqlcluster/deploy/ndb_data',

        # create my.cnf file
        '''echo "[mysqld]
ndbcluster
datadir=/opt/mysqlcluster/deploy/mysqld_data
basedir=/opt/mysqlcluster/home/mysqlc
port=3306" > /opt/mysqlcluster/deploy/conf/my.cnf''',

        # create conf.ini file
        f'''echo "[ndb_mgmd]
hostname={DNS_private_addresses["Cluster_Master"]}
datadir=/opt/mysqlcluster/deploy/ndb_data
nodeid=1

[ndbd default]
noofreplicas=3
datadir=/opt/mysqlcluster/deploy/ndb_data

[ndbd]
hostname={DNS_private_addresses["Cluster_Slave_1"]}
nodeid=3

[ndbd]
hostname={DNS_private_addresses["Cluster_Slave_2"]}
nodeid=4

[ndbd]
hostname={DNS_private_addresses["Cluster_Slave_3"]}
nodeid=5

[mysqld]
nodeid=50" > /opt/mysqlcluster/deploy/conf/config.ini''',

        # install and config mysql and node management
        '/opt/mysqlcluster/home/mysqlc/scripts/mysql_install_db --basedir=/opt/mysqlcluster/home/mysqlc --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data',
        '/opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf/'
    ]

    return commands

def create_commands_cluster_slaves(DNS_private_addresses):
    """
    Creates a lists of the commands to run on the slave instances we connected into via paramiko to connect them to the management node

    Parameters
    ----------
    DNS_private_addresses : dict(str -> str)
        Values are the private DNS addresses of each instance. The key is the instance's name.

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        'mkdir -p /opt/mysqlcluster/deploy/ndb_data',

        # link slave nodes to the dns private address of the management node
        f'/opt/mysqlcluster/home/mysqlc/bin/ndbd -c {DNS_private_addresses["Cluster_Master"]}'
    ]

    return commands

def create_commands_cluster_master_2():
    """
    Creates a lists of the commands to run only on the master instance to start mysqlc on the management node

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        # Start mysqlc management node
        '/opt/mysqlcluster/home/mysqlc/bin/mysqld --defaults-file=/opt/mysqlcluster/deploy/conf/my.cnf --user=root &'
    ]

    return commands

def create_commands_cluster_master_3():
    """
    Creates a lists of the commands to run only on the master instance to set up the users, password and sakila.

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        # create myapp user and set a password
        '''sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "CREATE USER 'myapp'@'%' IDENTIFIED BY 'testpwd';GRANT ALL PRIVILEGES ON * . * TO 'myapp'@'%' IDENTIFIED BY 'MyNewPass' WITH GRANT OPTION MAX_QUERIES_PER_HOUR 0 MAX_CONNECTIONS_PER_HOUR 0 MAX_UPDATES_PER_HOUR 0 MAX_USER_CONNECTIONS 0 ;"''',
        '''sudo /opt/mysqlcluster/home/mysqlc/bin/mysql -e "USE mysql; UPDATE user SET plugin='mysql_native_password' WHERE User='root'; FLUSH PRIVILEGES;SET PASSWORD FOR 'root'@'localhost' = PASSWORD('MyNewPass');"''',
        
        # Download sakila db
        'wget https://downloads.mysql.com/docs/sakila-db.tar.gz',
        'tar -xvf sakila-db.tar.gz',
        'rm sakila-db.tar.gz',

        # Add sakila to mysql and use it
        '''/opt/mysqlcluster/home/mysqlc/bin/mysql -h 127.0.0.1 -e "SOURCE sakila-db/sakila-schema.sql;" -u root -pMyNewPass''',
        '''/opt/mysqlcluster/home/mysqlc/bin/mysql -h 127.0.0.1 -e "SOURCE sakila-db/sakila-data.sql;" -u root -pMyNewPass''',
        '''/opt/mysqlcluster/home/mysqlc/bin/mysql -h 127.0.0.1 -e "USE sakila;" -u root -pMyNewPass'''
    ]

    return commands

def create_commands_sysbenchmark(threads, tables, mode, options="", table_size=100000):
    """
    Creates a lists of the commands to run the MySQL Benchmark with Sysbench

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        # create read queries
        f"sudo sysbench {mode} --table-size={table_size} --threads={threads} --tables={tables} --mysql-db=sakila --mysql-user=root --db-driver=mysql {options} prepare",
        # run read queries
        f"sudo sysbench {mode} --histogram --table-size={table_size} --threads={threads} --tables={tables} --mysql-db=sakila --mysql-user=root --db-driver=mysql {options} run",
        # cleanup data
        f"sudo sysbench {mode} --table-size={table_size} --threads={threads} --tables={tables} --mysql-db=sakila --mysql-user=root --db-driver=mysql --db-ps-mode=disable {options} cleanup"
    ]

    return commands


def ssh_connect_and_execute(paramiko_client, DNS_public_address, paramiko_key, commands, print_std=True):
    """
    Connects to the instance via paramiko and executes the given commands
    Prints out the stdout of the commands

    Parameters
    ----------
    paramiko_client: SSHClient
        The paramiko client we use for connection
    DNS_public_address : str
        public DNS address of the instance to connect into
    paramiko_key: RSAKey
        the labsuser.pem key used to connect to the AWS session
    commands: list of str
        list of the bash commands to run one after another on the instance
    print_std: bool (optional)
        By default True, will print the stdout. If False, doesn't print anything
    Returns
    -------
    None
    """
    import time 
    print("Connecting to ", DNS_public_address)
    paramiko_client.connect( hostname = DNS_public_address, username = "ubuntu", pkey = paramiko_key )
    print("Connected")
    
    for command in commands:
        print("Executing {}".format( command ))
        stdin , stdout, stderr = paramiko_client.exec_command(command)

        while print_std:
            print(stdout.readline())
            if stdout.channel.exit_status_ready():
                break

    time.sleep(10)
    
    return None


def ssh_connect_and_execute_save(paramiko_client, DNS_public_address, paramiko_key, commands, output_name, readline_start=False, readline_stop=False):
    """
    Connects to the instance via paramiko and executes the given commands
    Prints out the stdout of the commands

    Parameters
    ----------
    paramiko_client: SSHClient
        The paramiko client we use for connection
    DNS_public_address : str
        public DNS address of the instance to connect into
    paramiko_key: RSAKey
        the labsuser.pem key used to connect to the AWS session
    commands: list of str
        list of the bash commands to run one after another on the instance
    print_std: bool (optional)
        By default True, will print the stdout. If False, doesn't print anything
    Returns
    -------
    None
    """
    import time 
    print("Connecting to ", DNS_public_address)
    paramiko_client.connect( hostname = DNS_public_address, username = "ubuntu", pkey = paramiko_key )
    print("Connected")
    
    for command in commands:
        print("Executing {}".format( command ))
        stdin , stdout, stderr = paramiko_client.exec_command(command)
        if command.split(" ")[-1]=="run":
            output = open(f'{output_name}.txt','w+')
            output.write(" ".join(stdout.readlines()))
            output.close()
        else:
            print(stdout.read())
            print(stderr.read())
        
        time.sleep(5)

    time.sleep(10)

    return None