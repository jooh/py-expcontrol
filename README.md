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
clone this repo and do `python setup.py install`. Or just to 'pip install
expcontrol'.

# Do I need [psychopy](http://psychopy.org)?
In theory, no. All the psychopy-dependent code is in the psychopydep
module, so psychopy could be swapped out for another timing/opengl/response
logging solution as desired. In practice, psychopy is the only solution
that is implemented. For now, we list psychopy as a formal dependency but
this may change in the future.

# Development stage
Very early days. Use at your own risk.

# License
ISC. See [separate file](LICENSE).
