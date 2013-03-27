from fabric.api import *
from fabric.contrib.console import confirm

env.hosts = ["kraken.habhub.org"]

def run_tests():
    with settings(warn_only=True):
        result = local("nosetests")
    if result.failed and not confirm("Tests failed. Continue regardless?"):
        abort("Aborting due to failed tests.")

def deploy_code(habitat):
    code_dir = "/home/{0}/habitat".format(habitat)
    with settings(sudo_user=habitat):
        with cd(code_dir):
            sudo("git fetch origin")
            sudo("git merge --ff-only origin/develop")

def install_requirements(habitat):
    pip = "/home/{0}/venv/bin/pip".format(habitat)
    reqs = "/home/{0}/habitat/requirements.txt".format(habitat)
    sudo("{0} install -r {1}".format(pip, reqs))

def restart_parser(habitat):
    sudo("supervisorctl restart {0}:{0}-parser".format(habitat))

def restart_cnp(habitat):
    name = "{0}/venv/bin/couch-named-python".format(habitat)
    sudo("pkill -TERM -f {0} -U couchdb".format(name))

def upload_docs(habitat):
    db = habitat.replace("-", "_")
    vs = "cnp_{0}".format(db)
    user = prompt("CouchDB username?")
    password = prompt("CouchDB password?")
    url = "http://{0}:{1}@localhost:5984".format(user, password)
    path = "/home/{0}/venv/bin/cnp-upload".format(habitat)
    doc = "/home/{0}/habitat/couchdb/designdocs.yml".format(habitat)
    with settings(sudo_user=habitat):
        sudo("{path} --view-server={vs} {url} {db} {doc}".format(**locals()))

def deploy():
    targets = ("habitat", "habitat-beta")
    target = prompt("Deploy target? {0}".format(targets),
                    validate=lambda x: dict(zip(targets, targets))[x])
    run_tests()
    deploy_code(target)
    if confirm("Reinstall requirements?"):
        install_requirements(target)
    if confirm("Restart parser?"):
        restart_parser(target)
    if confirm("Reupload docs?"):
        upload_docs(target)
        if confirm("Restart CNP?"):
            restart_cnp(target)
