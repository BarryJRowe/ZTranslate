#/bin/bash
cd ..
../ENV_client/bin/python setup.py install
cd ztrans_client
../../ENV_client/bin/python ./startup.py
