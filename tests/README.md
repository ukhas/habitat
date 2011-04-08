# habitat tests

The python backend of habitat is tested using nosetests, and the front end
portion is tested using jasmine-node. The Makefile in the tests directory
expects to be able to use a nosetests and jasmine-node command, but if
they're not on the path, alternatives can be specified as follows:

    make JASMINE=/home/user/path/to/jasmine/run NOSETESTS=/opt/whatever/nt
