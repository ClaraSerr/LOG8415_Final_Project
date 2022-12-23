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

# Get the instance ID of the instance whose name is 'proxy'
Proxy_ip = instance_proxy['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Master_ip = instance_master['Reservations'][0]['Instances'][0]["PublicIpAddress"]

url = 'http://'+Proxy_ip+'/query'
print(Master_ip)
data = {
    'host': '127.0.0.1',
    'port': 3306,
    'ssh_host': Master_ip,
    'ssh_user': 'ubuntu',
    'db_host': 'localhost',
    'db_user': 'root',
    'db_password': 'MyNewPass',
    'db_name': 'sakila',
    'query': '''SELECT * FROM actor LIMIT 10;'''
}

headers = {'Content-Type': 'application/json'}
print(url)
print(data)

response = requests.post(url, json=data, headers=headers)

# if response.status_code == 200:
#     result = response.json()
print(response.text)
# else:
#     print('Request failed')
# Send a GET request to the app

# response = requests.get('http://3.81.167.97:80/')
# print(response.text)  # prints 'Hello, World!'

# # Test the /users/<id> route
# response = requests.get('http://3.81.167.97:80/users/1')
# print(response)  # prints {'name': 'John', 'age': 30}

# # Test a non-existent user
# response = requests.get('http://3.81.167.97:80/users/3')
# print(response)  # prints {'error': 'User not found'}
