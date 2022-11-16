import boto3
from botocore.exceptions import ClientError
import paramiko
import pymysql
import time
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import pandas as pd

# import as global variables
ec2_RESSOURCE = boto3.resource('ec2', region_name='us-east-1')
ec2_CLIENT = boto3.client('ec2')

def create_security_group(Vpcid, ports):
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
        # TODO TO DO add inbound rule ALL ICMP - IPv4 
        for port in ports: # In our use case, ports = [22, 80, 443]
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
                                'Description': "Flask_authorize"
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
                                'Description': "Flask_authorize"
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

def create_instance(instance_type,keyname,name,security_id,availability_zone):
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
        'yes | sudo apt-get install mysql-server',
        # Download Sakila database
        'wget https://downloads.mysql.com/docs/sakila-db.tar.gz',

        # Unpack sakila
        'tar -xf sakila-db.tar.gz',
        # Remove compressed folder
        'rm sakila-db.tar.gz',
        'sudo mysql -e "SOURCE sakila-db/sakila-schema.sql;"',
        'sudo mysql -e "SOURCE sakila-db/sakila-data.sql;"',
        'sudo mysql -e "USE sakila;"'
    ]
    return commands

def create_commands_cluster():
    """
    Creates a lists of the commands to run on the cluster instances we connected into via paramiko

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        'sudo apt-get update',
        'sudo mkdir -p /opt/mysqlcluster/home',
        'sudo chmod -R 777 /opt/mysqlcluster',
        'cd /opt/mysqlcluster/home',
        'wget http://dev.mysql.com/get/Downloads/MySQL-Cluster-7.2/mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'tar xvf mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'ln -s mysql-cluster-gpl-7.2.1-linux2.6-x86_64 mysqlc',
        'rm mysql-cluster-gpl-7.2.1-linux2.6-x86_64.tar.gz',
        'sudo chmod -R 777 /etc/profile.d',
        'echo "export MYSQLC_HOME=/opt/mysqlcluster/home/mysqlc" > /etc/profile.d/mysqlc.sh',
        'echo "export PATH=$MYSQLC_HOME/bin:$PATH" >> /etc/profile.d/mysqlc.sh',
        'source /etc/profile.d/mysqlc.sh',
        'sudo apt-get update && sudo apt-get -y install libncurses5'
    ]

    return commands

def create_commands_cluster_master(DNS_addresses):
    """
    Creates a lists of the commands to run on the master instances we connected into via paramiko

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        'mkdir -p /opt/mysqlcluster/deploy',
        'cd /opt/mysqlcluster/deploy',
        'mkdir conf',
        'mkdir mysqld_data',
        'mkdir ndb_data',
        'cd conf',
        '''echo "[mysqld]
ndbcluster
datadir=/opt/mysqlcluster/deploy/mysqld_data
basedir=/opt/mysqlcluster/home/mysqlc
port=3306" > my.cnf''',
        f'''echo "[ndb_mgmd]
hostname={DNS_addresses["Cluster_Master"]}
datadir=/opt/mysqlcluster/deploy/ndb_data
nodeid=1

[ndbd default]
noofreplicas=3
datadir=/opt/mysqlcluster/deploy/ndb_data

[ndbd]
hostname={DNS_addresses["Cluster_Slave_1"]}
nodeid=3

[ndbd]
hostname={DNS_addresses["Cluster_Slave_2"]}
nodeid=4

[ndbd]
hostname={DNS_addresses["Cluster_Slave_3"]}
nodeid=5

[mysqld]
nodeid=50" > config.ini''',
        'cd /opt/mysqlcluster/home/mysqlc',
        'scripts/mysql_install_db --no-defaults --datadir=/opt/mysqlcluster/deploy/mysqld_data',
        'sudo /opt/mysqlcluster/home/mysqlc/bin/ndb_mgmd -f /opt/mysqlcluster/deploy/conf/config.ini --initial --configdir=/opt/mysqlcluster/deploy/conf/',
        

    ]

    return commands

def create_commands_cluster_slaves(DNS_addresses):
    """
    Creates a lists of the commands to run on the slave instances we connected into via paramiko

    Returns
    -------
    list
        list of the commands to run
    """
    commands = [
        'mkdir -p /opt/mysqlcluster/deploy/ndb_data',
        f'sudo /opt/mysqlcluster/home/mysqlc/bin/ndbd -c {DNS_addresses["Cluster_Master"]}'
    ]

    return commands

def main():
    """
    main script for the final project
    """

    Vpcid = ec2_CLIENT.describe_vpcs().get('Vpcs', [{}])[0].get('VpcId', '')
    
    # Launches custom security group
    security_group_id = create_security_group(Vpcid, [22, 80, 443])

    # Launches all instances
    MySQL = {}
    MySQL_ID = {}

    MySQL["Stand_Alone"] = create_instance("t2.micro","vockey","mySQL_Stand_Alone",security_group_id,"us-east-1a")
    MySQL_ID["Stand_Alone"] = MySQL["Stand_Alone"].instance_id

    MySQL["Cluster_Master"] = create_instance("t2.micro","vockey","mySQL_Cluster_Master",security_group_id,"us-east-1b")
    MySQL_ID["Cluster_Master"] = MySQL["Cluster_Master"].instance_id

    
    for i in range(1,4):
        MySQL[f"Cluster_Slave_{i}"]=create_instance("t2.micro","vockey",f"mySQL_Cluster_Slave_{i}",security_group_id,"us-east-1b")
        MySQL_ID[f"Cluster_Slave_{i}"]=MySQL[f"Cluster_Slave_{i}"].instance_id


    DNS_addresses={}
    IP_addresses={}

    for key in MySQL:
        MySQL[key].wait_until_running()
        # Reload the instance attributes
        MySQL[key].load()
        DNS_addresses[key] = MySQL[key].private_dns_name
        IP_addresses[key] = MySQL[key].public_ip_address
        print("DNS = ",MySQL[key].private_dns_name)
        print("IPV4 = ",MySQL[key].public_ip_address)
        # Enable detailed monitoring
        MySQL[key].monitor(
            DryRun=False
        )
    
    # Configure SSH connection to AWS
    k = paramiko.RSAKey.from_private_key_file("labsuser.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # wait to make sure connection will be possible
    time.sleep(10)

    for key in MySQL:
        print("Connecting to ", IP_addresses[key])
        c.connect( hostname = IP_addresses[key], username = "ubuntu", pkey = k )
        print("Connected")

        commands_sakila = create_commands_sakila()
 
        for command in commands_sakila:
            print("Executing {}".format( command ))
            stdin , stdout, stderr = c.exec_command(command)
            print(stdout.read())
            print(stderr.read())
        c.close()
        # The last command to be executed does not send anything to stdout, so we don't read it not to be stuck
        '''print("Executing {}".format( commands_sakila[-1] ))
        stdin , stdout, stderr = c.exec_command(commands_sakila[-1])
        print("Go to http://"+str(IP_addresses_t2[i]))'''
        with sshtunnel.open_tunnel(
            (IP_addresses[key], 22),
            ssh_username="ubuntu",
            ssh_pkey=k,
            remote_bind_address=('127.0.0.1', 3306),
            local_bind_address=('127.0.0.1', 3306)) as tunnel:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('127.0.0.1', 3306)
            #conn = pymysql.connect(host='127.0.0.1', user="ubuntu", port=tunnel.local_bind_port)
            query_1 = '''SOURCE sakila-db/sakila-schema.sql;'''
            query_2 = '''SOURCE sakila-db/sakila-data.sql;'''
            query_3 = '''USE sakila;'''

            data = pd.read_sql_query(query_1, client)
            print(data)
            data = pd.read_sql_query(query_2, client)
            print(data)
            data = pd.read_sql_query(query_3, client)
            print(data)
            client.close()

    time.sleep(5)
    

    print('Launching complete')

main()