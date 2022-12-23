import boto3
from botocore.exceptions import ClientError
import time

# import as global variables
ec2_RESSOURCE = boto3.resource('ec2', region_name='us-east-1')
ec2_CLIENT = boto3.client('ec2')

## Delete all instances

instances = ec2_CLIENT.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': ['proxy']}, {'Name': 'instance-state-name', 'Values': ['running']}])
# Get the instance ID of the instance whose name is 'proxy'
instance_id = [instances['Reservations'][0]['Instances'][0]['InstanceId']]
print(instance_id)
# Remove instances
ec2_CLIENT.terminate_instances(InstanceIds=(instance_id))
print("Instances removed")