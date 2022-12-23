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

resp = ec2_CLIENT.describe_instances()
# Lists the id of all instances
running_instances = [instance['Instances'][0]['InstanceId'] for instance in resp['Reservations'] if instance['Instances'][0]['State']['Name'] == 'running']

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
print(running_instances)
print(vpcid)
print(vpc)
print(L[0])


def create_commands_flask(key):
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
    '''echo '{}' >> key.pem'''.format(key),
    'sudo chmod 400 key.pem',
    '''echo "from flask import Flask, request
from sshtunnel import SSHTunnelForwarder
import pymysql
import pandas as pd
import paramiko

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, Forld!'

@app.route('/users/<id>')
def get_user(id):
    # You can replace this with a database query or some other logic to fetch a user
    users = {1: {'name': 'John', 'age': 30}, 2: {'name': 'Jane', 'age': 25}}
    user = users.get(int(id))
    if not user:
        return 'User not found', 404
    return 'Name: '+user['name']+', Age: '+str(user['age'])

@app.route('/query', methods=['POST'])
def query_database():
    # Parse the request data
    data = request.get_json()
    host_ = data['host']
    port = data['port']
    ssh_host = data['ssh_host']
    ssh_user = data['ssh_user']
    ssh_key = paramiko.RSAKey.from_private_key_file('key.pem')
    db_host = data['db_host']
    db_user = data['db_user']
    db_password = data['db_password']
    db_name = data['db_name']
    query = data['query']

    with SSHTunnelForwarder(
            (ssh_host, 22),
            ssh_username=ssh_user,
            ssh_pkey=ssh_key,
            remote_bind_address=(db_host, port)) as tunnel:
        conn = pymysql.connect(host=host_, user=db_user,
                passwd=db_password, db=db_name,
                port=tunnel.local_bind_port)
        received = pd.read_sql_query(query, conn)
        conn.close()
    
    # Return the query result
    return str(received)

if __name__ == '__main__':
     app.run(host='0.0.0.0', port=80)" | sudo tee app.py  ''',


    # nohup is used to keep the application running
    # the argument is the public IPV4 address of the instance, used to define the server name 
    'sudo nohup env "PATH=$PATH" python3 app.py &'
    ]
    return commands


def ssh_connect_and_execute_except_last(paramiko_client, DNS_public_address, paramiko_key, commands, IP_address):
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
    print("Executing {}".format( commands[-1] ))
    stdin , stdout, stderr = paramiko_client.exec_command(commands[-1])
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
f= open("labsuser.pem",'r')
key=f.read()
f.close()
ssh_connect_and_execute_except_last(c, DNS_public_addresses["Proxy"], k, create_commands_flask(key), IP_addresses["Proxy"])

time.sleep(10)