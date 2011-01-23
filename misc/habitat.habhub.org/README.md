# habitat.habhub.org miscellanea

The scripts here live and run on [[nessie.habhub.org]].

 - runas.c (compiles to runas): setugid CGI binary configured to be run by
   the web server whenever a certain url is fetched. This url is installed
   as a github post-receive hook. The setugid binary provides a secure way
   to go from running as www-data, to running as habitat-www in order to
   regenerate the [sphinx documentation](http://habitat.habhub.org/).
   Also locks a file to ensure that simultaneous updating isn't attempted.
 - update: bash script - pulls the latest git repo, builds the documentation,
   cleans the repo, generates a tarball, updates the homepage.
 - genhomepage: bash script - generates
   [[http://habitat.habhub.org/index.html]] with the latest commit message.
 - sanitise.py: utility for genhomepage - escapes xml special characters.

