import argparse
import subprocess
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import zipfile

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
def send_email_with_attachment(smtp_server, smtp_port, sender_email, app_password, recipient_email, ovpn_file_path):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = "OpenVPN Configuration Files"

    body = "Import the files into OpenVPN. Download OpenVPN here if you don't have it already --> https://openvpn.net/downloads/openvpn-connect-v3-windows.msi. Download the zip folder to a local directory and extract it. Then double-click on 'open_port.bat' and log into Netflix in your browser within 3 minutes. Your VPN will then disconnect, and you'll use your own network for internet."
    message.attach(MIMEText(body, "plain"))

    # Create a zip folder
    zip_folder_path = "openvpn_config.zip"
    with zipfile.ZipFile(zip_folder_path, 'w') as zip_file:
        # Add the client.ovpn file
        zip_file.write(ovpn_file_path, os.path.basename(ovpn_file_path))

        # Add open_port.bat
        open_port_bat_path = "open_port.bat"
        zip_file.write(open_port_bat_path, os.path.basename(open_port_bat_path))

        # Add close_port.bat
        close_port_bat_path = "close_port.bat"
        zip_file.write(close_port_bat_path, os.path.basename(close_port_bat_path))

    # Attach the zip folder
    with open(zip_folder_path, "rb") as zip_attachment:
        part = MIMEApplication(zip_attachment.read(), Name=os.path.basename(zip_folder_path))
        part["Content-Disposition"] = f"attachment; filename={os.path.basename(zip_folder_path)}"
        message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

    # Remove the temporary zip folder
    os.remove(zip_folder_path)

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
            ovpn_file_path = f'client{i}.ovpn'
            send_email_with_attachment(smtp_server, smtp_port, sender_email, app_password, recipient_email, ovpn_file_path)

if __name__ == "__main__":
    main()
