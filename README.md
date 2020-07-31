# kronofoto

Hopefully all tests will pass when you run tests:

    ./manage.py test
    
Currently the test script writes out a ton of jpeg files while testing and doesn't delete them. That should be fixed at some point.

There is a command to load existing data from the standard arbitrary csv format. This command only loads records into a table that will not be needed later. 

    ./manage.py importcsv fortepandata.csv

Another command attempts to find images in a directory and associate them with those records. It's currently misses a lot of info.

    ./manage.py findphotos testphotos/
    
You may also need to build the search index:

    ./manage.py build_index

The test server can then be started up:

    ./manage.py runserver 0.0.0.0:8000
