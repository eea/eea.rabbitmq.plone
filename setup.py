# -*- coding: utf-8 -*-


from setuptools import setup, find_packages
import os

version = open('version.txt').read().strip()

setup(name='eea.rabbitmq.plone',
      version=version,
      description="EEA RabbitMQ Plone - plone add-on.",
      long_description=open("README.txt").read() + "\n" +
      open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "Programming Language :: Python",
      ],
      keywords='rabbitmq plone',
      author='Ghiță Bizău',
      author_email="ghita.bizau@eaudeweb.ro",
      url='https://github.com/eea/eea.rabbitmq.plone.git',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['eea', 'eea.rabbitmq'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.api',
          'eea.rabbitmq.client',
      ],
      extras_require={
          'test': [
              'setuptools',
              'plone.api',
              'eea.rabbitmq.client',
              'plone.app.testing',
          ],
      },
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
