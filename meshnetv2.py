import argparse
import subprocess
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

def generate_ca():
    subprocess.run("openssl genpkey -algorithm RSA -out ca.key", shell=True)
    subprocess.run("openssl req -x509 -new -key ca.key -out ca.crt -days 365 -subj '/CN=OpenVPN-CA'", shell=True)

def generate_dh_params():
    subprocess.run("openssl dhparam -out dh.pem 2048", shell=True)

def generate_server_certificates():
    subprocess.run("openssl genpkey -algorithm RSA -out server.key", shell=True)
    subprocess.run("openssl req -new -key server.key -out server.csr -subj '/CN=OpenVPN-Server'", shell=True)
    subprocess.run("openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365", shell=True)
    subprocess.run("openvpn --genkey secret ta.key", shell=True)

def generate_client_certificates(client_name):
    subprocess.run(f"openssl genpkey -algorithm RSA -out {client_name}.key", shell=True)
    subprocess.run(f"openssl req -new -key {client_name}.key -out {client_name}.csr -subj '/CN={client_name}'", shell=True)
    subprocess.run(f"openssl x509 -req -in {client_name}.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out {client_name}.crt -days 365", shell=True)

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
<auth-user-pass>
</auth-user-pass>
<tls-auth>
{open('ta.key', 'r').read()}
</tls-auth>
"""
    with open(f'{client_name}.ovpn', 'w') as client_config_file:
        client_config_file.write(client_config)

    os.remove(f'{client_name}.csr')
    os.remove(f'{client_name}.key')
    os.remove(f'{client_name}.crt')

def generate_server_config():
    dh_params = open('dh.pem', 'r').read()
    ca_cert = open('ca.crt', 'r').read()
    server_cert = open('server.crt', 'r').read()
    server_key = open('server.key', 'r').read()
    ta_key = open('ta.key', 'r').read()

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
<tls-auth>
{ta_key}
</tls-auth>
auth-user-pass-verify /tmp/auth-script.sh via-env
username-as-common-name
script-security 3
"""
    with open('server.conf', 'w') as server_config_file:
        server_config_file.write(server_config)

    os.remove('ca.key')
    os.remove('ca.crt')
    os.remove('server.crt')
    os.remove('server.key')
    os.remove('dh.pem')
    os.remove('ta.key')
    if os.path.exists('server.csr'):
        os.remove('server.csr')
    if os.path.exists('ca.srl'):
        os.remove('ca.srl')

def generate_auth_script(username, password):
    auth_script_content = f"""#!/bin/bash
echo "{username}"
echo "{password}"
"""
    script_path= '/tmp/auth-script.sh'

    #write script content to file
    with open('/tmp/auth-script.sh', 'w') as auth_script:
        auth_script.write(auth_script_content)

    os.chmod(script_path, 0o700)
    subprocess.run(['awk', 'NF {print $0}', script_path])

def send_email_with_attachment(smtp_server, smtp_port, sender_email, app_password, recipient_email, ovpn_file_path):
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = "OpenVPN Configuration File"

    body = f"Please import the attached OpenVPN configuration file into the OpenVPN app. Use the following username and password when connecting:\n\nUsername: {username}\nPassword: {password}\nWindows OpenVPN Download: https://openvpn.net/downloads/openvpn-connect-v3-windows.msi\nApple IOS OpenVPN Download: https://apps.apple.com/us/app/openvpn-connect-openvpn-app/id590379981\n\nHave a great day!"
    message.attach(MIMEText(body, "plain"))

    with open(ovpn_file_path, "rb") as attachment:
        ovpn_part = MIMEApplication(attachment.read(), _subtype="ovpn")
        ovpn_part.add_header("Content-Disposition", f"attachment; filename=client.ovpn")
        message.attach(ovpn_part)

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls(context=context)
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, message.as_string())

def start_openvpn_server():
    subprocess.run("openvpn --config server.conf --auth-user-pass-verify /tmp/auth-script.sh via-env", shell=True)

def main():
    global args, username, password
    parser = argparse.ArgumentParser(description='Generate OpenVPN configuration and certificates.')
    parser.add_argument('-e', '--email', type=str, help='Outlook email address', required=True)
    parser.add_argument('-p', '--password', type=str, help='App Password for Outlook email', required=True)
    parser.add_argument('-s', '--server-ip', type=str, help='Server public IP', required=True)
    parser.add_argument('-a', '--auth', type=str, help='Basic Authentication user:password', required=True)

    args = parser.parse_args()
    username, password = args.auth.split(':')

    # Generate CA
    generate_ca()

    # Generate Diffie-Hellman parameters
    generate_dh_params()

    # Generate server certificates
    generate_server_certificates()

    # Generate client certificates
    num_clients = int(input("Enter the number of clients to create: "))
    for i in range(1, num_clients + 1):
        generate_client_certificates(f'client{i}')

    # Generate server configuration
    generate_server_config()

    # Generate authentication script
    generate_auth_script(username, password)

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

    # Start OpenVPN server
    start_server_choice = input("Do you want to start the OpenVPN server now? (yes/no): ").lower()
    if start_server_choice == "yes":
        start_openvpn_server()

if __name__ == "__main__":
    main()
