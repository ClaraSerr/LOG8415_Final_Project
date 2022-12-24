import requests
import boto3
from botocore.exceptions import ClientError
import time
import paramiko

# import as global variables
ec2_RESSOURCE = boto3.resource('ec2', region_name='us-east-1')
ec2_CLIENT = boto3.client('ec2')

instance_proxy = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['proxy']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_master = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Master']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_slave_1 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_1']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_slave_2 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_2']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_slave_3 = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Slave_3']}, {'Name': 'instance-state-name', 'Values': ['running']}])

# Get the instance ID of the instance whose name is 'proxy'
Proxy_ip = instance_proxy['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Master_ip = instance_master['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Slave_1_ip = instance_slave_1['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Slave_2_ip = instance_slave_2['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Slave_3_ip = instance_slave_3['Reservations'][0]['Instances'][0]["PublicIpAddress"]

url = 'http://'+Proxy_ip+'/query'
headers = {'Content-Type': 'application/json'}
print(Master_ip)
print(url)

# data_1 = {
#     'mode': 1,
#     'host': '127.0.0.1',
#     'port': 3306,
# #    'ssh_host': Master_ip,
#     'ssh_user': 'ubuntu',
#     'db_user': 'root',
#     'db_password': 'MyNewPass',
#     'db_name': 'sakila',
#     'query': '''SELECT * FROM actor LIMIT 10;'''
# }

# print(data_1)

# response_1 = requests.post(url, json=data_1, headers=headers)

# print(response_1.text)

data_2 = {
    'mode': 2,
    'host': '127.0.0.1',
    'port': 3306,
    # 'ssh_host': Master_ip,
    'ssh_user': 'ubuntu',
    'db_user': 'root',
    'db_password': 'MyNewPass',
    'db_name': 'sakila',
    'query': '''SELECT * FROM actor LIMIT 5;'''
}
print(data_2)

response_2 = requests.post(url, json=data_2, headers=headers)

print(response_2.text)