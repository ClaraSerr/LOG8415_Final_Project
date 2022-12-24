from sshtunnel import SSHTunnelForwarder
import pymysql
import requests
import boto3
from botocore.exceptions import ClientError
import time
import paramiko
import pandas as pd
# import as global variables
ec2_RESSOURCE = boto3.resource('ec2', region_name='us-east-1')
ec2_CLIENT = boto3.client('ec2')

instance_proxy = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['proxy']}, {'Name': 'instance-state-name', 'Values': ['running']}])
instance_master = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['mySQL_Cluster_Master']}, {'Name': 'instance-state-name', 'Values': ['running']}])

# Get the instance ID of the instance whose name is 'proxy'
Proxy_ip = instance_proxy['Reservations'][0]['Instances'][0]["PublicIpAddress"]
Master_ip = instance_master['Reservations'][0]['Instances'][0]["PublicIpAddress"]

k = paramiko.RSAKey.from_private_key_file("labsuser.pem")

print(Master_ip)
data = {
    'host': '127.0.0.1',
    'port': 3306,
    'ssh_host': Master_ip,
    'ssh_user': 'ubuntu',
    'ssh_key': k,
    'db_host': 'localhost',
    'db_user': 'root',
    'db_password': 'MyNewPass',
    'db_name': 'sakila',
    'query': '''SELECT * FROM actor LIMIT 10;'''
}
print(data)
host = data['host']
port = data['port']
ssh_host = data['ssh_host']
ssh_user = data['ssh_user']
ssh_key= data['key']
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
    conn = pymysql.connect(host='127.0.0.1', user=db_user,
            passwd=db_password, db=db_name,
            port=tunnel.local_bind_port)
    query = '''SELECT * FROM actor LIMIT 10;'''
    data = pd.read_sql_query(query, conn)
    conn.close()
    print(data)

# # Set up the SSHTunnelForwarder
# with SSHTunnelForwarder(
#     (ssh_host, 22),
#     ssh_username=ssh_user,
#     remote_bind_address=(host, port)
# ) as tunnel:
#     # Forward the request through the tunnel
#     print('tunnel start')
#     tunnel.start()
#     # Connect to the database using pymysql
#     connection = pymysql.connect(
#         host=db_host,
#         port=tunnel.local_bind_port,
#         user=db_user,
#         password=db_password,
#         db=db_name
#     )
#     try:
#         print('try')
#         with connection.cursor() as cursor:
#             # Execute the query and retrieve the results
#             cursor.execute(query)
#             result = cursor.fetchall()
#     finally:
#         connection.close()
#     tunnel.stop()