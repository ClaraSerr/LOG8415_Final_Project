import boto3
from botocore.exceptions import ClientError
import paramiko
import pymysql
import time
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import requests
from utils import *

ec2_RESSOURCE = boto3.resource('ec2')
ec2_CLIENT = boto3.client('ec2')

# Lists the id of all instances
instance_slave_1 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_1']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_slave_2 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_2']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_slave_3 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_3']}, {'Name': 'instance-state-name', 'Values': ['running']}])

# Get the instance ID of the instance whose name is 'proxy'
Slave_1_ip = instance_slave_1['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Slave_2_ip = instance_slave_2['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Slave_3_ip = instance_slave_3['Reservations'][0]['Instances'][0]["PublicIpAddress"]
response = ec2_CLIENT.describe_vpcs()
vpcid = response.get('Vpcs', [{}])[0].get('VpcId', '')

vpc = ec2_RESSOURCE.Vpc(vpcid)

security_groups_dict = ec2_CLIENT.describe_security_groups()
security_groups = security_groups_dict['SecurityGroups']
L=[]
for groupobj in security_groups:
    # We don't want to remove the default security group
    if groupobj['GroupName']!='default':
        L.append(groupobj['GroupId'])
security_group_id=L[0]
print(vpcid)
print(vpc)
print(L[0])


def create_commands_flask(key, access_key_id, secret_access_key, session_token):
    ### stores in a list the set of commands needed to deploy Flask on an instance
    commands = ['sudo add-apt-repository universe',
    'sudo apt-get update',
    #'yes | sudo apt-get upgrade', 
    'yes | sudo apt-get install python3-pip',
    # adds to path the location of the flask module
    'export PATH="/home/ubuntu/.local/bin:$PATH"',
    'sudo pip3 install Flask',
    'sudo pip3 install sshtunnel',
    'sudo pip3 install pymysql',
    'sudo pip3 install paramiko',
    'sudo pip3 install pandas',
    'sudo pip3 install awscli',
    'sudo pip3 install boto3',
    '''echo '{}' >> key.pem'''.format(key),
    'sudo chmod 400 key.pem',
    f'''echo "from flask import Flask, request
from sshtunnel import SSHTunnelForwarder
import boto3
import pymysql
import pandas as pd
import paramiko
import random

ec2_CLIENT = boto3.client('ec2',region_name='us-east-1',
    aws_access_key_id='{access_key_id}',
    aws_secret_access_key='{secret_access_key}',
    aws_session_token='{session_token}')
'''+'''
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, Forld!'

@app.route('/query', methods=['POST'])
def query_database():
    instance_master = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Master']}, {'Name': 'instance-state-name', 'Values': ['running']}])
    Master_ip = instance_master['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(Master_ip)
    # Parse the request data
    data = request.get_json()
    mode = data['mode']
    host_ = data['host']
    port = data['port']
    ssh_host = Master_ip
    ssh_user = data['ssh_user']
    ssh_key = paramiko.RSAKey.from_private_key_file('key.pem')
    db_user = data['db_user']
    db_password = data['db_password']
    db_name = data['db_name']
    query = data['query']

    if mode == 1:    
        with SSHTunnelForwarder(
                (ssh_host, 22),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key,
                remote_bind_address=('127.0.0.1', port)) as tunnel:
            conn = pymysql.connect(host=host_, user=db_user,
                    passwd=db_password, db=db_name,
                    port=tunnel.local_bind_port)
            received = pd.read_sql_query(query, conn)
            conn.close()
    
    if mode == 2:
        i = random.randint(1, 3)
        instance_slave = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [f'mySQL_Cluster_Slave_{i}']}, {'Name': 'instance-state-name', 'Values': ['running']}])
        Slave_ip = instance_slave['Reservations'][0]['Instances'][0]['PublicIpAddress']
        print(Slave_ip)
        with SSHTunnelForwarder(
                (ssh_host, 22),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key,
                remote_bind_address=(Slave_ip, 3306),
                local_bind_address=('127.0.0.1', 3306)) as tunnel:
            conn = pymysql.connect(host='localhost', user=db_user,
                    passwd=db_password, db=db_name,
                    port=tunnel.local_bind_port)
            received = pd.read_sql_query(query, conn)
            conn.close()
    
    if mode == 3:
        instance_slave_1 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_1']}, {'Name': 'instance-state-name', 'Values': ['running']}])
        instance_slave_2 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_2']}, {'Name': 'instance-state-name', 'Values': ['running']}])
        instance_slave_3 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_3']}, {'Name': 'instance-state-name', 'Values': ['running']}])
        Slave_id_1 = instance_slave['Reservations'][0]['Instances'][0]['InstanceId']
        Slave_id_2 = instance_slave['Reservations'][0]['Instances'][0]['InstanceId']
        Slave_id_3 = instance_slave['Reservations'][0]['Instances'][0]['InstanceId']

        PINGS={}
        PINGS[f'Slave_id_1']=ec2_CLIENT.ping(InstanceId=Slave_id_1)['Latency']['Value']
        PINGS[f'Slave_id_2']=ec2_CLIENT.ping(InstanceId=Slave_id_2)['Latency']['Value']
        PINGS[f'Slave_id_3']=ec2_CLIENT.ping(InstanceId=Slave_id_3)['Latency']['Value']

        instance_id_min = min(PINGS, key=PINGS.get)
        instance_ip=ec2_CLIENT.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicIpAddress']
        with SSHTunnelForwarder(
                (ssh_host, 22),
                ssh_username=ssh_user,
                ssh_pkey=ssh_key,
                remote_bind_address=(instance_ip, port)) as tunnel:
            conn = pymysql.connect(host=host_, user=db_user,
                    passwd=db_password, db=db_name,
                    port=tunnel.local_bind_port,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor)

            cursor = conn.cursor()
            cursor.execute(query)

            # Fetch the results of the query
            received = cursor.fetchall()

            # Close the cursor and connection
            cursor.close()
            conn.close()

    # Return the query result
    return str(received)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)" | sudo tee app.py  ''',


    # nohup is used to keep the application running
    # the argument is the public IPV4 address of the instance, used to define the server name 
    'sudo nohup env "PATH=$PATH" python3 app.py &'
    ]
    return commands


def ssh_connect_and_execute_except_last(paramiko_client, DNS_public_address, paramiko_key, commands, IP_address):
    """
    Connects to the instance via paramiko and executes the given commands
    Prints out the stdout of the commands except for the last command that starts the Flask application and doesn't return anything

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
    IP_address: str
        The public IP address to send the queries
    Returns
    -------
    None
    """
    print("Connecting to ", DNS_public_address)
    paramiko_client.connect( hostname = DNS_public_address, username = "ubuntu", pkey = paramiko_key )
    print("Connected")

    for command in commands[:-1]:
        print("Executing {}".format( command ))
        stdin , stdout, stderr = paramiko_client.exec_command(command)
        print(stdout.read())
        print(stderr.read())
        time.sleep(5)
        
        # The last command to be executed does not send anything to stdout, so we don't read it not to be stuck
    # print("Executing {}".format( commands[-1] ))
    # stdin , stdout, stderr = paramiko_client.exec_command(commands[-1])
    print("Go to http://"+str(IP_address))
    time.sleep(10)

    return None

Cloud_Patterns = {}
Cloud_Patterns_ID = {}
Cloud_Patterns["Proxy"] = create_instance(ec2_RESSOURCE, "t2.large","vockey","proxy",security_group_id,"us-east-1a")
Cloud_Patterns_ID["Proxy"] = Cloud_Patterns["Proxy"].instance_id

DNS_public_addresses={}
DNS_private_addresses={}
IP_addresses={}

    
for instance in Cloud_Patterns:
    Cloud_Patterns[instance].wait_until_running()

    # Reload the instance attributes
    Cloud_Patterns[instance].load()
    DNS_private_addresses[instance] = Cloud_Patterns[instance].private_dns_name
    DNS_public_addresses[instance] = Cloud_Patterns[instance].public_dns_name
    IP_addresses[instance] = Cloud_Patterns[instance].public_ip_address
    print("DNS public = ",Cloud_Patterns[instance].public_dns_name)
    print("DNS private = ",Cloud_Patterns[instance].private_dns_name)
    print("IPV4 = ", Cloud_Patterns[instance].public_ip_address)

# Configure SSH connection to AWS
k = paramiko.RSAKey.from_private_key_file("labsuser.pem")
c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())

time.sleep(15)

# Start the Proxy
f_1= open("labsuser.pem",'r')
key=f_1.read()
f_1.close()

f_2= open("creds.txt",'r')
creds=f_2.read()
f_2.close()

lines = creds.strip().split('\n')

# Extract the values of the aws_access_key_id, aws_secret_access_key, and aws_session_token
# variables from the lines
access_key_id = lines[1].split('=')[1]
secret_access_key = lines[2].split('=')[1]
session_token = lines[3].split('=')[1]

ssh_connect_and_execute_except_last(c, DNS_public_addresses["Proxy"], k, create_commands_flask(key, access_key_id, secret_access_key, session_token), IP_addresses["Proxy"])

time.sleep(10)