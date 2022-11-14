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
echo "[default]
aws_access_key_id=ASIAXRQOSDSKNUAP5THD
aws_secret_access_key=8dwsqDyR682Qi/Rf+dGnSMZv9ODkG4tZmHokCN/9
aws_session_token=FwoGZXIvYXdzEOH//////////wEaDH+cGDiI69t2Ar7jRSLCAVEFxvB1bcHt3xkTDrnWDt4K/+4N2MzSIGUiqYUTLRGalvYaXj8Wj0tNwfUXX7tOLbrLic+EB9uhUZ4c/UlE7O520mWgXPoFT2+McjHvuHCgxJGcZP5Udy7IYjrBX+xoN8ZbemqctAaun+3yr0mQhVEeuxgFpvZdnGoQO9ExBPvdaOKFi82or6CRDs2gjRXEhg3ki4215p8ekyeudgTz3FbM729ieLQ+DVmp76UZ4HKatXQEqoYbBYmU/LwT3hfSalmPKL+FxpsGMi3jzz2nPApm3NsYDJoRw6WYaraquy+vNQyVukK2CZ6SFUPpCW0ECydcphNtV1s=" > ~/.aws/credentials

# Start the execution
python3 launching.py
