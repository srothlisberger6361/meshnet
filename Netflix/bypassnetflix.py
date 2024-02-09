import argparse
import subprocess
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# Function to generate CA key and certificate
def generate_ca():
    subprocess.run("openssl genpkey -algorithm RSA -out ca.key", shell=True)
    subprocess.run("openssl req -x509 -new -key ca.key -out ca.crt -days 365 -subj '/CN=OpenVPN-CA'", shell=True)

# Function to generate Diffie-Hellman parameters
def generate_dh_params():
    subprocess.run("openssl dhparam -out dh.pem 2048", shell=True)

# Function to generate server certificates
def generate_server_certificates():
    subprocess.run("openssl genpkey -algorithm RSA -out server.key", shell=True)
    subprocess.run("openssl req -new -key server.key -out server.csr -subj '/CN=OpenVPN-Server'", shell=True)
    subprocess.run("openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365", shell=True)

# Function to generate client certificates
def generate_client_certificates(client_name):
    subprocess.run(f"openssl genpkey -algorithm RSA -out {client_name}.key", shell=True)
    subprocess.run(f"openssl req -new -key {client_name}.key -out {client_name}.csr -subj '/CN={client_name}'", shell=True)
    subprocess.run(f"openssl x509 -req -in {client_name}.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out {client_name}.crt -days 365", shell=True)

    # Create client OpenVPN configuration file
    client_config = f"""
client
dev tun
tun-mtu 1500
mssfix
proto udp
route 0.0.0.0 0.0.0.0 10.8.0.1
remote {args.server_ip} 50000
resolv-retry infinite
nobind
persist-key
persist-tun
verb 3
pull
redirect-gateway def1 bypass-dhcp
<ca>
{open('ca.crt', 'r').read()}
</ca>
<cert>
{open(f'{client_name}.crt', 'r').read()}
</cert>
<key>
{open(f'{client_name}.key', 'r').read()}
</key>
"""
    with open(f'{client_name}.ovpn', 'w') as client_config_file:
        client_config_file.write(client_config)

    # Delete unnecessary files
    os.remove(f'{client_name}.csr')
    os.remove(f'{client_name}.key')
    os.remove(f'{client_name}.crt')

# Function to generate server configuration
def generate_server_config():
    dh_params = open('dh.pem', 'r').read()
    ca_cert = open('ca.crt', 'r').read()
    server_cert = open('server.crt', 'r').read()
    server_key = open('server.key', 'r').read()

    server_config = f"""
dev tun
tun-mtu 1500
mssfix
proto udp
port 50000
server 10.8.0.0 255.255.255.0
ifconfig-pool-persist /var/log/openvpn/ipp.txt
push "route 10.8.0.0 255.255.255.0"
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
keepalive 10 120
<dh>
{dh_params}
</dh>
<ca>
{ca_cert}
</ca>
<cert>
{server_cert}
</cert>
<key>
{server_key}
</key>
persist-key
persist-tun
status /var/log/openvpn/openvpn-status.log
verb 3
"""
    with open('server.conf', 'w') as server_config_file:
        server_config_file.write(server_config)

    # Delete unnecessary files
    os.remove('ca.key')
    os.remove('ca.crt')
    os.remove('server.crt')
    os.remove('server.key')
    os.remove('dh.pem')
    if os.path.exists('server.csr'):
        os.remove('server.csr')
    if os.path.exists('ca.srl'):
        os.remove('ca.srl')

# Function to send email with attachment
def send_email_with_attachment(smtp_server, smtp_port, sender_email, app_password, recipient_email, file_paths):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = "OpenVPN Configuration Files"

    body = "Download OpenVPN here if you don't have it already --> https://openvpn.net/downloads/openvpn-connect-v3-windows.msi. Rename open_port.txt and close_port.txt to open_port.bat and close_port.bat. Then, double click open_port.bat and login to netflix in a browser within 3 minutes. Happy watching!"
    message.attach(MIMEText(body, "plain"))

    for file_path in file_paths:
        # Change extension of bat files to txt
        if file_path.endswith('.bat'):
            file_path_txt = f"{os.path.splitext(file_path)[0]}.txt"
            with open(file_path, "rb") as attachment:
                part = MIMEApplication(attachment.read(), Name=os.path.basename(file_path_txt))
                message.attach(part)
        else:
            with open(file_path, "rb") as attachment:
                part = MIMEApplication(attachment.read(), Name=os.path.basename(file_path))
                message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

# Main function
def main():
    global args
    parser = argparse.ArgumentParser(description='Generate OpenVPN configuration and certificates.')
    parser.add_argument('-e', '--email', type=str, help='Outlook email address', required=True)
    parser.add_argument('-p', '--password', type=str, help='App Password for Outlook email', required=True)
    parser.add_argument('-s', '--server-ip', type=str, help='Server public IP', required=True)

    args = parser.parse_args()

    # Generate CA
    generate_ca()

    # Generate Diffie-Hellman parameters
    generate_dh_params()

    # Generate server certificates
    generate_server_certificates()

    # Generate client certificates (replace 'client1' with desired client name)
    num_clients = int(input("Enter the number of clients to create: "))
    for i in range(1, num_clients + 1):
        generate_client_certificates(f'client{i}')

    # Generate server configuration
    generate_server_config()

    # Email configuration files
    send_email_choice = input("Do you want to send OVPN files to clients via email? (yes/no): ").lower()
    if send_email_choice == "yes":
        smtp_server = "smtp-mail.outlook.com"
        smtp_port = 587
        sender_email = args.email
        app_password = args.password

        for i in range(1, num_clients + 1):
            recipient_email = input(f"Enter email for client{i}: ")
            file_paths = [f'client{i}.ovpn', 'open_port.bat', 'close_port.bat']
            send_email_with_attachment(smtp_server, smtp_port, sender_email, app_password, recipient_email, file_paths)

if __name__ == "__main__":
    main()
