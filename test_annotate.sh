#!/bin/sh

sed -i 's/parser.add_argument/parser.function_does_not_exit/g' ./upload.py
python ./upload.py -f cmocka 2>&1 > annotate.log
sed -i 's/parser.function_does_not_exit/parser.add_argument/g' ./upload.py