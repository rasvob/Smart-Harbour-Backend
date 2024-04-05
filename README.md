# Backend solution for the Smart Harbour project
* FastAPI
* Database - MariaDB or PostgreSQL

## Self-signed certificate generation
Create the CA Certificate first
> openssl req -x509 -sha256 -days 356 -nodes -newkey rsa:2048 -subj "/CN=example.vsb.cz/C=US/L=Ostrava" -keyout rootCA.key -out rootCA.crt

Create the Server Private Key
> openssl genrsa -out server.key 2048

Create CSR - csr.conf

~~~
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[ dn ]
C = CZ
ST = Czechia
L = Ostrava
O = FEI
OU = K460
CN = example.vsb.cz

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = example.vsb.cz
DNS.2 = www.example.vsb.cz
IP.1 = 158.196.145.183
~~~

Generate Certificate Signing Request (CSR) Using Server Private Key
> openssl req -new -key server.key -out server.csr -config csr.conf

Create cert.conf

~~~
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.vsb.cz
~~~

Generate SSL certificate With self signed CA
> openssl x509 -req -in server.csr -CA rootCA.crt -CAkey rootCA.key -CAcreateserial -out server.crt -days 365 -sha256 -extfile cert.conf