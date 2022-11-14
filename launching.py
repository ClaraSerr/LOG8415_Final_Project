import boto3
from botocore.exceptions import ClientError
import paramiko
import pymysql
import time
import sshtunnel
from sshtunnel import SSHTunnelForwarder

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


def create_commands_sakila():
    """
    Creates a lists of the commands to run on the instances we connected into via paramiko

    Returns
    -------
    list
        list of the commands to run
    """
    
    commands = ['sudo apt-get update', 
    'yes | sudo apt-get install mysql-server',
    # Download Sakila database
    'wget https://downloads.mysql.com/docs/sakila-db.tar.gz',

    # Unpack sakila
    'tar -xf sakila-db.tar.gz',
    # Remove compressed folder
    'rm sakila-db.tar.gz'
    ]

    '''

    # python script containing the application definition
    ''''''echo "import sys
from flask import Flask
app = Flask(__name__)
@app.route('/{}')
def myFlaskApp():
    return 'Instance number {} is responding now!'
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80) " | sudo tee app.py ''''''.format(cluster_number,instance_number),
    # nohup is used to keep the application running
    # the argument is the public IPV4 address of the instance, used to define the server name 
    'sudo nohup env "PATH=$PATH" python3 app.py &']'''
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
        DNS_addresses[key] = MySQL[key].public_dns_name
        IP_addresses[key] = MySQL[key].public_ip_address
        print("DNS = ",MySQL[key].public_dns_name)
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
        with SSHTunnelForwarder(
            (IP_addresses[key], 22),
            ssh_username="ubuntu",
            ssh_pkey=k,
            remote_bind_address=(IP_addresses[key], 22)) as tunnel:
            conn = pymysql.connect(host='127.0.0.1', user="ubuntu",
                    port=tunnel.local_bind_port)
            query_1 = '''SOURCE sakila-db/sakila-schema.sql;'''
            query_2 = '''SOURCE sakila-db/sakila-data.sql;'''
            query_3 = '''USE sakila;'''

            data = pd.read_sql_query(query_1, conn)
            print(data)
            data = pd.read_sql_query(query_2, conn)
            print(data)
            data = pd.read_sql_query(query_3, conn)
            print(data)
            conn.close()

    time.sleep(5)
    

    print('Launching complete')

main()