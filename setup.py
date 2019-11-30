from setuptools import setup, find_packages

__VERSION__ = "1.0.0"

def main(args=None):
    README = open("./README").read()

    setup_required_packages = []

    required_packages = [
                         "pymongo>=2.8,<=2.9.0", #"tornado==5.0.2", 
                         "Pillow==5.1.0", #"elasticsearch>=6.0.0,<7.0.0"
                         "opencv-python==3.4.3.18", "numpy==1.15.2",
                         "imutils", "fuzzywuzzy",
                         "pytesseract==0.2.4",#"pycrypto==2.6", "pycurl"
                        ]

    test_required_packages = ["nose", "coverage"]

    settings = dict(name="ztranslate_common",
                    version=__VERSION__,
                    description="ztranslate",
                    long_description=README,
                    classifiers=["Programming Language :: Python", ],
                    author="",
                    author_email="",
                    url="",
                    keywords="ztranslate",
                    packages=find_packages(),
                    include_package_data=True,
                    zip_safe=False,
                    install_requires=required_packages,
                    tests_require=test_required_packages,
                    test_suite="nose.collector",
                    setup_requires=setup_required_packages,
                    entry_points="""\
                        [console_scripts] 
                        """,
                    )
    if args:
        settings['script_name'] = __file__
        settings['script_args'] = args
    setup(**settings)


if __name__ == "__main__":
    main()
