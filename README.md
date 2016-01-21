This package is designed to enable quick and easy development of
experiments in psychology/neuroscience. Most experiment scripts are coded
up with a fairly ad-hoc `for t in trials` approach, which generally leads
to inaccurate timing, accumulation of lag over trials, and in catastrophic
cases, failure to log all the experimental parameters and responses of
interest. It can also be surprisingly difficult to achieve more
sophisticated presentation schemes (e.g., presenting a video while
collecting keyboard responses and monitoring MRI scanner pulses) if you are
coding everything up from scratch.

# Install
clone this repo and do `python setup.py install`. A reasonably recent
version should also be on [pypi](https://pypi.python.org/pypi/expcontrol)
so try `pip install expcontrol`. TODO: there will be pre-built packages on
[my anaconda repository](https://anaconda.org/jcarlin) soon.

# Do I need [psychopy](http://psychopy.org)?
At the moment you do, but the goal is to remove this dependency eventually.
All the psychopy-dependent code is in the psychopydep module, so psychopy
could be swapped out for another timing/opengl/response logging solution as
desired.

# Development stage
Very early days. Use at your own risk. Basic behavioural testing should
work.

# TO DO
* Eye tracker interface with Eyelink
* Scanner pulse and other serial interface fun stuff
* Auditory events

# License
ISC. See [separate file](LICENSE).
