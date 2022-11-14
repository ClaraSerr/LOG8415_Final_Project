# LOG8415_Final_Project

#MySQL StandAlone

# Create security group with 3 inbound and outbound rules port 22 80 443 custom TCP 0.00.00/
# Create instance ubuntu vockey Custom security group t2.micro

# Connect to aws instance
ssh -i labsuser.pem ubuntu@<Public IPv4 address>

# Install MySQL
sudo apt-get update
yes | sudo apt-get install mysql-server

# Download Sakila database
wget https://downloads.mysql.com/docs/sakila-db.tar.gz

tar -xf sakila-db.tar.gz
rm sakila-db.tar.gz

# Log in as root user
sudo mysql

# Create sakila db

SOURCE sakila-db/sakila-schema.sql;
SOURCE sakila-db/sakila-data.sql;
USE sakila;

