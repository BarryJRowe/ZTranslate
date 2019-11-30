#!/bin/bash
cd ..
../ENV/bin/python setup.py install
cd ztrans_common
../../ENV/bin/python opencv_engine.py
