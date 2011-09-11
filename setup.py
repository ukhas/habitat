from setuptools import setup

setup(
    name="habitat",
    version="0.2dev",
    author="HABHUB Team",
    author_email="root@habhub.org",
    url="http://habitat.habhub.org/",
    description="Next Generation High Altitude Balloon Tracking",
    packages=["habitat", "habitat.parser_modules", "habitat.sensors",
        "habitat.utils"],
    scripts=["bin/habitat", "bin/sign_hotfix"],
    license="GNU General Public License Version 3",
    install_requires=["M2Crypto>=0.21.1", "couchdbkit>=0.5.4", "crcmod>=1.7",
        "ipaddr>=2.1.9"],
)
