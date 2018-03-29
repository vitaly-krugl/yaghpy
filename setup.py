"""
Setup for Yet Another GitHub API Python wrapper (experimental)
"""

import setuptools

name = 'yagpy'

setuptools.setup(
    name='yagpy',
    version='0.0.1',
    description='Yet Another GitHub API Python wrapper (experimental);',
    author='Vitaly Kruglikov',
    author_email='vitaly.krugl.github@gmail.com',
    url='https://github.com/vitaly-krugl/yagpy',
    license='BSD',
    package_dir = {'': 'src'},
    packages=setuptools.find_packages('src'),
    zip_safe=True,
    entry_points={
        'console_scripts': [
            ('ghtoporgrepos = {}.top_org_repos:top_org_repos'.format(name))
        ]
    },
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English', 'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Communications', 'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Networking'
    ],

)
