import psychopy.core
import psychopy.visual
import psychopy.logging
import psychopy.event

class clock(object):
    '''
    Time-keeping functionality for expcontrol by wrapping Psychopy's
    core.Clock instance.'''

    def __init__(self):
        '''Initialise a clock instance.'''
        self.ppclock = psychopy.core.Clock()
        psychopy.logging.setDefaultClock(self.ppclock)
        return

    def __call__(self):
        '''Return the current time stamp from ppclock.getTime'''
        return self.ppclock.getTime()

    def start(self):
        '''Reset the clock to 0.'''
        self.ppclock.reset()
        return self.ppclock.getTime()

class window(object):
    '''
    Display control functionality for expcontrol by wrapping
    Psychopy's visual.Window.
    '''

    def __init__(self,*args,**kwargs):
        '''
        Initialise a window instance. All input arguments are piped to
        psychopy.visual.Window.
        '''
        self.ppwin = psychopy.visual.Window(*args,**kwargs)
        return

    def __call__(self):
        return self.ppwin.flip()

    def close(self):
        self.ppwin.close()
        return

class KeyboardResponse(object):
    esckey = 'escape'

    def __init__(self,keylist):
        keylist.append(self.esckey)
        self.keylist = keylist
        return

    def __call__(self):
        k = psychopy.event.getKeys(keyList=self.keylist)
        if self.esckey in k:
            psychopy.core.quit()
        return k
