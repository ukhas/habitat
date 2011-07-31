from distutils.core import setup

setup(
    name="habitat",
    version="0.1dev",
    author="HABHUB Team",
    author_email="root@habhub.org",
    url="http://habitat.habhub.org/",
    description="Next Generation High Altitude Balloon Tracking",
    packages=["habitat", "habitat/parser_modules", "habitat/utils",
        "habitat/sensors",],
    license="GNU General Public License Version 3",
)
