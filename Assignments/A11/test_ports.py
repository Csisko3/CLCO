import socket #py lib for low level networking

def test_ports(ip, ports):
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            if result == 0:
                print(f"Port {port} is OPEN")
            else:
                print(f"Port {port} is CLOSED")

# Replace with your public IP
public_ip = "51.136.49.196"

# List of ports to test
ports_to_check = [22, 80, 443, 3389] # SSH, HTTP, HTTPS, RDP (Windows)
# 22 might work bc of default nsg rule from Azure ? 

test_ports(public_ip, ports_to_check)

# also testable with nmap or telnet