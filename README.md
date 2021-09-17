# kronofoto

# Install the dependencies:

You must use Python 3. Optionally, you probably should use a virtual environment:

    python -m venv kfenv
    source kfenv/bin/activate
    
Install dependencies:

    python -m pip install -r requirements.txt

# Configure kronofoto:

Copy the examplesettings.py file in the kronofoto directory to settings.py. Fill in the missing values.

Hopefully all tests will pass when you run tests:

    ./manage.py test
    
Currently the test script writes out a ton of jpeg files while testing and doesn't delete them. That should be fixed at some point.

Run the migrations:

    ./manage.py migrate

Create the cache table:

    ./manage.py createcachetable

There is a command to load existing data from the standard arbitrary csv format. This command only loads records into a table that will not be needed later. 

    ./manage.py importcsv fortepandata.csv

Another command attempts to find images in a directory and associate them with those records. It's currently misses a lot of info.

    ./manage.py findphotos testphotos/
    
You may also need to build the search index:

    ./manage.py build_index

The test server can then be started up:

    ./manage.py runserver 0.0.0.0:8000
