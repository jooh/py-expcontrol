try: 
    from setuptools import setup
except ImportError: 
    from distutils.core import setup
import os
setup(name='expcontrol',
      version='0.1.1',
      author='Johan Carlin',
      author_email='johan.carlin@gmail.com',
      url='http://github.com/jooh/expcontrol',
      description= ('Easy control of typical experiments in psychology '
          'and neuroscience, including stimulus presentation, timing, '
          'response collection and logging.'),
      keywords = ['psychology','neuroscience','cognitive','psychopy',
          'vision','perception','experiment','science','research'],
      license='ISC',
      packages=['expcontrol'],
      install_requires = ['numpy','pandas','psychopy','sqlalchemy'],
      long_description=open(os.path.join(os.path.dirname(__file__),
          'README')).read()
      )
