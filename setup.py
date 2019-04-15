""" Installer
"""
import os
from setuptools import setup, find_packages

NAME = 'eea.rabbitmq.plone'
PATH = NAME.split('.') + ['version.txt']
VERSION = open(os.path.join(*PATH)).read().strip()

setup(name=NAME,
      version=VERSION,
      description="EEA RabbitMQ Plone - plone add-on.",
      long_description=open("README.txt").read() + "\n" +
      open(os.path.join("docs", "HISTORY.txt")).read(),
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Plone",
          "Framework :: Plone :: 4.3",
      ],
      keywords='EEA Add-ons Plone Zope RabbitMQ',
      author='European Environment Agency: IDM2 A-Team',
      author_email='eea-edw-a-team-alerts@googlegroups.com',
      url='https://github.com/eea/eea.rabbitmq.plone.git',
      namespace_packages=['eea', 'eea.rabbitmq'],
      packages=find_packages(exclude=['ez_setup']),
      include_package_data=True,
      license='GPL',
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.api',
          'eea.rabbitmq.client',
      ],
      extras_require={
          'test': [
              'plone.app.testing',
          ],
      },
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
