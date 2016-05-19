'''Expcontrol functionality that depends on psychopy.'''
import collections
import numpy
import psychopy.core
import psychopy.visual
import psychopy.logging
import psychopy.event
from psychopy.hardware.emulator import SyncGenerator

class Clock(object):
    '''
    Time-keeping functionality for expcontrol by wrapping Psychopy's
    core.Clock instance.'''

    def __init__(self):
        '''Initialise a clock instance.'''
        self.ppclock = psychopy.core.Clock()
        super(Clock, self).__init__()
        psychopy.logging.setDefaultClock(self.ppclock)
        return

    def __call__(self):
        '''Return the current time stamp from ppclock.getTime'''
        return self.ppclock.getTime()

    def start(self):
        '''Reset the clock to 0.'''
        self.ppclock.reset()
        return self()

    def wait(self, time):
        '''wait for time duration (s).'''
        psychopy.core.wait(time)
        return

    def waituntil(self, time):
        '''wait until the clock reaches time.'''
        self.wait(time-self())
        return

class PulseClock(Clock):
    '''
    Time-keeping with tracking of pulses (e.g. from a scanner trigger)
    through a keyboard button at some interval. Note that time is
    still tracked in seconds, not pulses. So on its own, using this class
    will ensure that you synchronise your experiment to the first pulse
    (see start method), but everything afterwards still runs in seconds as
    with the standard Clock class.

    The only further refinement is that the clock will attempt to meausure
    pulse period empirically whenever given a chance (ie, self.waituntil is
    called with enough remaining time that a pulse is expected during the
    wait. These estimates are stored in self.periodhistory.
    '''
    def __init__(self, key, period, pulsedur=0.01, tolerance=.1, timeout=20., \
                 verbose=False, ndummies=0):
        self.period = period
        self.pulsedur = pulsedur
        self.tolerance = tolerance
        self.periodhistory = [period]
        self.timeout = timeout
        self.verbose = verbose
        assert ndummies >= 0, 'ndummies must be 0 or greater'
        self.ndummies = ndummies
        super(PulseClock, self).__init__()
        self.keyhand = KeyboardResponse(key, self.ppclock)
        return

    def waitpulse(self):
        '''wait until a pulse is received. An exception is raised if the wait
        exceeds self.timeout.'''
        key, keytime = self.keyhand.waitkey(self.timeout)
        assert key, 'exceeded %.0fs timeout without receiving pulse' % \
            self.timeout
        # first time of response if we got multiple
        keytime = keytime[0]
        return keytime

    def start(self):
        '''reset the clock and return once the correct pulse has been received
        (one for each of self.ndummies+1).'''
        # need to first reset the second clock to make the timeout counter
        # in waitpulse work properly
        super(PulseClock, self).start()
        # nb +1 so we always wait for a pulse. dummies are in ADDITION to this
        for dummy in range(self.ndummies+1):
            if self.verbose:
                print 'waiting for pulse %d' % dummy
                # but this means that the starttime recorded here is off
                starttime = self.waitpulse()
        # so we adjust the clock to compensate for starttime (not quite the
        # same as zeroing the clock - if time has passed since the pulse
        # was received this operation will produce a current clock time >0
        self.ppclock.add(starttime)
        # return current time after all this
        return self()

    def waituntil(self, time):
        '''wait until time, catching any pulses along the way.'''
        # current time
        now = self()
        nowpulse = now / self.period
        timepulse = time / self.period
        npulseleft = numpy.floor(timepulse)-numpy.floor(nowpulse)
        if npulseleft < 1:
            # less than a self.period left, so wait it out using standard
            # second clock
            super(PulseClock, self).waituntil(time)
            return
        # if we make it here, there must be pulses to catch
        actualtime = self.waitpulse()
        # we expect the next pulse to be number
        predictpulse = numpy.ceil(now / self.period)
        # now we can update our estimate of period like so...
        newpulse = actualtime / predictpulse
        if numpy.abs(newpulse-self.period) > self.tolerance:
            raise Exception('pulse period beyond tolerance: ' +
                            'expected=%.4f, estimated=%.4f' % (self.period,
                                                               newpulse))
        self.period = newpulse
        if self.verbose:
            print 'Pulse at %.2f. tr=%.3f' % (actualtime, newpulse)
        self.periodhistory.append(newpulse)
        # avoid catching the same pulse twice
        if (time-self()) > self.pulsedur:
            self.wait(self.pulsedur)
        # we recurse with a depth of npulseleft. This is important to
        # handle cases where you are waiting n pulses + a bit extra
        self.waituntil(time)
        return

class Window(object):
    '''
    Display control functionality for expcontrol by wrapping
    Psychopy's visual.Window.
    '''

    def __init__(self, *args, **kwargs):
        '''
        Initialise a window instance. All input arguments are piped to
        psychopy.visual.Window.
        '''
        self.winhand = psychopy.visual.Window(*args, **kwargs)
        # flip a few times because it is thought this helps stabilise
        # timings
        [self() for flip in range(50)]
        return

    def __call__(self):
        '''flip the screen and return an exact time stamp of when the flip
        occurred.'''
        return self.winhand.flip()

    def close(self):
        '''close the screen.'''
        self.winhand.close()
        return

class KeyboardResponse(object):
    '''
    Psychopy-based keyboard response checking.
    '''
    esckey = 'escape'

    def __init__(self, keylist, clock):
        '''
        Initialise a KeyboardResponse instance. keylist is a list of valid keys
        (all other inputs are ignored). clock is a handle to a current Psychopy
        clock instance.
        '''
        if not isinstance(keylist, collections.Iterable):
            keylist = [keylist]
        self.keylist = keylist + [self.esckey]
        self.ppclock = clock
        return

    def __call__(self):
        '''Check for responses.'''
        ktup = psychopy.event.getKeys(keyList=self.keylist,
                                      timeStamped=self.ppclock)
        return self.parsekey(ktup)

    def waitkey(self, dur=float('inf')):
        '''wait for a key press for a set duration (default inf).'''
        ktup = psychopy.event.waitKeys(maxWait=dur, keyList=self.keylist,
                                       timeStamped=self.ppclock)
        return self.parsekey(ktup)

    def parsekey(self, ktup):
        '''Convert timestamped key presses to separate key and time stamp
        arrays. Used internally to support __call__ and waitkey.'''
        keys = []
        timestamps = []
        if ktup:
            keys, timestamps = zip(*ktup)
        if self.esckey in keys:
            raise Exception('user pressed escape')
        return numpy.array(keys), numpy.array(timestamps)

class PulseEmulator(object):
    '''
    Simulate pulses at some period. Just a convenience wrapper for
    psychopy.hardware.emulator.SynchGenerator.
    '''
    def __init__(self, *args, **kwargs):
        '''Initialise a PulseEmulator instance. All arguments are passed to
        SynchGenerator.'''
        self.pulsehand = SyncGenerator(*args, **kwargs)
        return

    def start(self):
        '''Start sending pulses.'''
        self.pulsehand.start()
        psychopy.core.runningThreads.append(self.pulsehand)
        return

    def stop(self):
        '''Stop sending pulses.'''
        self.pulsehand.stop()
        return
