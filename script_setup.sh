#!/bin/bash

# Install required modules
pip3 install awscli
pip3 install boto3
pip3 install paramiko
pip3 install pymysql
pip3 install sshtunnel

# Move key to project folder
mv ~/Downloads/labsuser.pem ~/Documents/LOG8415/LOG8415_Final_Project/

# Change the permissions on the key to be read only
chmod 400 labsuser.pem

# Edit AWS CLI
echo "<AWS CLI>" > ~/.aws/credentials

# Start the execution
python3 launching.py
