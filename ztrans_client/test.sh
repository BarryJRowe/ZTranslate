#/bin/bash
cd ../..
rm -rf ENV_client
virtualenv ENV_client -p /usr/bin/python2.7
cd ztranslate_os
../ENV_client/bin/python setup.py install
cd ztrans_client
../../ENV_client/bin/python ./pipeline_general_service.py
