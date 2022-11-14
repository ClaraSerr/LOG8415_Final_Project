import boto3
from botocore.exceptions import ClientError
import time

# import as global variables
ec2_RESSOURCE = boto3.resource('ec2', region_name='us-east-1')
ec2_CLIENT = boto3.client('ec2')

## Delete all instances

Instances = ec2_CLIENT.describe_instances()

# Lists the id of all instances
Instances_id=[]
for reservation in Instances['Reservations']:
    for instance in reservation['Instances']:
        Instances_id.append(instance['InstanceId'])

try:
    # Remove instances
    ec2_CLIENT.terminate_instances(InstanceIds=(Instances_id))
    print("Instances removed")
except ClientError as e:
    print(e)

## Delete endpoints

Vpcid = ec2_CLIENT.describe_vpcs().get('Vpcs', [{}])[0].get('VpcId', '')
Endpoints = ec2_CLIENT.describe_vpc_endpoints(
            Filters=[{
                'Name': 'vpc-id',
                'Values': [Vpcid]
            }])['VpcEndpoints']

try:
    # Remove endpoints
    for ep in Endpoints:
        ec2_CLIENT.delete_vpc_endpoints(VpcEndpointIds=[ep['VpcEndpointId']])
except ClientError as e:
    print(e)

time.sleep(40)

## Delete Security Group

Security_groups = ec2_CLIENT.describe_security_groups()['SecurityGroups']
# We don't want to remove the default security group
Security_groups_not_default=[]
for group in Security_groups:
    if group['GroupName']!='default':
        Security_groups_not_default.append(group['GroupId'])

try:
    # Remove Security Group
    for sg in Security_groups_not_default:
        response = ec2_CLIENT.delete_security_group(GroupId=sg)
        print('Security Group Deleted', response)
except ClientError as e:
    print(e)