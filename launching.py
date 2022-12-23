import boto3
from botocore.exceptions import ClientError
import paramiko
import pymysql
import time
import sshtunnel
from sshtunnel import SSHTunnelForwarder
import requests
from utils import *

# import as global variables
ec2_RESSOURCE = boto3.resource('ec2', region_name='us-east-1')
ec2_CLIENT = boto3.client('ec2')

def main():
    """
    main script for the final project
    For every dict, the keys are:
        "Stand_Alone"
        "Cluster_Master"
        "Cluster_Slave_1"
        "Cluster_Slave_2"
        "Cluster_Slave_3"
    """

    Vpcid = ec2_CLIENT.describe_vpcs().get('Vpcs', [{}])[0].get('VpcId', '')
    
    # Launches custom security group
    security_group_id = create_security_group(ec2_RESSOURCE, ec2_CLIENT, ClientError, Vpcid, [22, 80, 443, 1186, 3306, 5000])

    # Launches all instances and stores their value (into MySQL) and id (into MySQL_ID)
    MySQL = {}
    MySQL_ID = {}


    MySQL["Stand_Alone"] = create_instance(ec2_RESSOURCE, "t2.micro","vockey","mySQL_Stand_Alone",security_group_id,"us-east-1a")
    MySQL_ID["Stand_Alone"] = MySQL["Stand_Alone"].instance_id

    MySQL["Cluster_Master"] = create_instance(ec2_RESSOURCE, "t2.micro","vockey","mySQL_Cluster_Master",security_group_id,"us-east-1b")
    MySQL_ID["Cluster_Master"] = MySQL["Cluster_Master"].instance_id

    for i in range(1,4):
        MySQL[f"Cluster_Slave_{i}"]=create_instance(ec2_RESSOURCE, "t2.micro","vockey",f"mySQL_Cluster_Slave_{i}",security_group_id,"us-east-1b")
        MySQL_ID[f"Cluster_Slave_{i}"]=MySQL[f"Cluster_Slave_{i}"].instance_id


    # Go through each instance to get their addresses
    DNS_public_addresses={}
    DNS_private_addresses={}
    IP_addresses={}

    for instance in MySQL:
        MySQL[instance].wait_until_running()

        # Reload the instance attributes
        MySQL[instance].load()
        DNS_private_addresses[instance] = MySQL[instance].private_dns_name
        DNS_public_addresses[instance] = MySQL[instance].public_dns_name
        IP_addresses[instance] = MySQL[instance].public_ip_address
        print("DNS public = ",MySQL[instance].public_dns_name)
        print("DNS private = ",MySQL[instance].private_dns_name)
        print("IPV4 = ", MySQL[instance].public_ip_address)


    # Configure SSH connection to AWS
    k = paramiko.RSAKey.from_private_key_file("labsuser.pem")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # wait to make sure connection will be possible
    time.sleep(10)

    #Stand Alone and sakila
    ssh_connect_and_execute(c, DNS_public_addresses["Stand_Alone"], k, create_commands_stand_alone())

    #Common Steps on all Nodes
    for key in MySQL:
        if key!="Stand_Alone":
            ssh_connect_and_execute(c, DNS_public_addresses[key], k, create_commands_cluster())
            time.sleep(10)

    #On the Cluster_Master
    ssh_connect_and_execute(c, DNS_public_addresses["Cluster_Master"], k, create_commands_cluster_master_1(DNS_private_addresses))
    
    #On the Cluster slaves
    for i in range(1,4):
        ssh_connect_and_execute(c, DNS_public_addresses[f"Cluster_Slave_{i}"], k, create_commands_cluster_slaves(DNS_private_addresses))

    #On the Cluster_Master, start the mysqlc management node. We need to wait for the process to iddle before proceeding
    ssh_connect_and_execute(c, DNS_public_addresses["Cluster_Master"], k, create_commands_cluster_master_2(), False)
    time.sleep(180)

    #On the Custer Master, set up user, password and sakila
    ssh_connect_and_execute(c, DNS_public_addresses["Cluster_Master"], k, create_commands_cluster_master_3())


    # Benchmark the MySQL Stand Alone
    for i in range(1,4):
        ssh_connect_and_execute_save(c, DNS_public_addresses["Stand_Alone"], k, create_commands_sysbenchmark(4, 4, "oltp_read_only"),f"output_stand_alone_read_t4_{i}")
        ssh_connect_and_execute_save(c, DNS_public_addresses["Stand_Alone"], k, create_commands_sysbenchmark(8, 8, "oltp_read_only"),f"output_stand_alone_read_t8_{i}")
        ssh_connect_and_execute_save(c, DNS_public_addresses["Stand_Alone"], k, create_commands_sysbenchmark(2, 4, "oltp_read_write --delete_inserts=2 --index_updates=2 --non_index_updates=2"),f"output_stand_alone_write_t2_{i}")
        ssh_connect_and_execute_save(c, DNS_public_addresses["Stand_Alone"], k, create_commands_sysbenchmark(4, 10, "oltp_read_write --delete_inserts=5 --index_updates=5 --non_index_updates=5"),f"output_stand_alone_write_t4_{i}")


    # Benchmark the MySQL Cluster
    for i in range(1,4):
        ssh_connect_and_execute_save(c, DNS_public_addresses["Cluster_Master"], k, create_commands_sysbenchmark(4, 4, "oltp_read_only", "--mysql-host=127.0.0.1 --mysql-password=MyNewPass"),f"output_cluster_read_t4_{i}")
        ssh_connect_and_execute_save(c, DNS_public_addresses["Cluster_Master"], k, create_commands_sysbenchmark(8, 8, "oltp_read_only", "--mysql-host=127.0.0.1 --mysql-password=MyNewPass"),f"output_cluster_read_t8_{i}")
        ssh_connect_and_execute_save(c, DNS_public_addresses["Cluster_Master"], k, create_commands_sysbenchmark(2, 4, "oltp_read_write --delete_inserts=2 --index_updates=2 --non_index_updates=2", "--mysql-host=127.0.0.1 --mysql-password=MyNewPass"),f"output_cluster_write_t2_{i}")
        ssh_connect_and_execute_save(c, DNS_public_addresses["Cluster_Master"], k, create_commands_sysbenchmark(4, 10, "oltp_read_write  --delete_inserts=5 --index_updates=5 --non_index_updates=5", "--mysql-host=127.0.0.1 --mysql-password=MyNewPass"),f"output_cluster_write_t4_{i}")

    time.sleep(10)


    print(DNS_public_addresses)
    c.close()

    print('Launching complete')

main()