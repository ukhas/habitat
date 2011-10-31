============
Certificates
============

The certificates folder contains x509 certificate files which are used to
verify the authenticity of hotfix code.

As hotfix code is run live from the CouchDB database, habitat uses certificates
to check that the code can be trusted. The habitat developers maintain a
certificate authority, whose certificate is included as
`ca/habitat_ca_cert.pem`, which is used to sign code-signing certificates.

Hotfix code then has its SHA-256 digest signed by the developer's private key,
and this is verified by habitat before the code is executed.

You can add new CA certificates to the `ca` folder, and new code-signing
certificates to the `certs` folder, as you please. Hotfix code references a
certificate filename found in the `certs` folder.

Generating a Private Key
------------------------

.. code-block:: bash

    $ openssl genrsa -des3 4096 > private.pem
    $ openssl req -new -key private.pem -out req.csr

Now send req.csr to us and we can sign it with the habitat CA and give you the
signed certificate.

Generating a Certificate Authority
----------------------------------

This is a fair bit more complex. Consider using tools such as tinyca or
gnomint.

Signing Code
------------

.. code-block:: bash

    $ vi my_hotfix_code.py
    $ habitat/bin/sign_hotfix my_hotfix_code.py ~/my_rsa_key.pem

The printed result is a JSON object which can be placed into the filters list
on a flight document.
