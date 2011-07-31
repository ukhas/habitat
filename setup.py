from setuptools import setup

setup(
    name="habitat",
    version="0.1dev",
    author="HABHUB Team",
    author_email="root@habhub.org",
    url="http://habitat.habhub.org/",
    description="Next Generation High Altitude Balloon Tracking",
    packages=["habitat", "habitat.parser_modules", "habitat.sensors",
        "habitat.utils", "tests.test_habitat", "tests.test_habitat.lib",
        "tests.test_habitat.test_archive", "tests.test_habitat.test_http",
        "tests.test_habitat.test_main",
        "tests.test_habitat.test_message_server",
        "tests.test_habitat.test_parser",
        "tests.test_habitat.test_parser_modules",
        "tests.test_habitat.test_sensor_manager",
        "tests.test_habitat.test_sensors", "tests.test_habitat.test_utils"],
    scripts=["bin/habitat", "bin/sign_hotfix"],
    license="GNU General Public License Version 3",
    install_requires=["M2Crypto>=0.21.1", "couchdbkit>=0.5.4", "crcmod>=1.7",
        "http-parser>=0.6.3", "ipaddr>=2.1.9", "restkit>=3.3.0",
        "wsgiref>=0.1.2"],
)
