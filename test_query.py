import requests
import boto3

# import as global variables
ec2_CLIENT = boto3.client('ec2')

instance_proxy = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['proxy']}, {'Name': 'instance-state-name', 'Values': ['running']}])
# Get the instance ID of the instance whose name is 'proxy'
Proxy_ip = instance_proxy['Reservations'][0]['Instances'][0]["PublicIpAddress"]

url = 'http://'+Proxy_ip+'/query'
headers = {'Content-Type': 'application/json'}

print(url)

print("MODE 1 DIRECT HIT: \n")
data_1 = {
    'mode': 1,
    'query': '''SELECT * FROM actor LIMIT 10;'''
}
print(data_1)
response_1 = requests.post(url, json=data_1, headers=headers)
print(response_1.text,'\n')

print("MODE 2 RANDOM: \n")
data_2 = {
    'mode': 2,
    'query': '''SELECT * FROM actor LIMIT 5;'''
}
print(data_2)
response_2 = requests.post(url, json=data_2, headers=headers)
print(response_2.text,'\n')

print("MODE 3 CUSTOMIZED: \n")
data_3 = {
    'mode': 3,
    'query': '''SELECT * FROM actor LIMIT 2;'''
}
print(data_3)
response_3 = requests.post(url, json=data_3, headers=headers)
print(response_3.text,'\n')