'''base expcontrol functionality.'''
import datetime
import functools
import numpy
from . import event

def addcustomdict(funhand):
    '''
    Decorator for save functionality (currently in Experiment class).
    '''
    @functools.wraps(funhand)
    def wrapper(*args, **kwargs): # pylint: disable=missing-docstring
        # a few assumptions here: 1) customdict is in kwargs, 2) res is in args
        if 'customdict' in kwargs and kwargs['customdict']:
            # assigning to args requires list type
            args = list(args)
            args[1] = args[1].copy()
            for extrafield, extraval in kwargs['customdict'].iteritems():
                args[1][extrafield] = extraval
        return funhand(*args, **kwargs)
    return wrapper

class Controller(object):
    '''
    Control experiment timing, stimulus delivery and response collection.
    '''

    def __init__(self, window=None, response=None, clock=None, eyetracker=None):
        '''
        Initialise a controller instance. For example inputs, see
        expcontrol.psychopydep.window, KeyboardResponse and clock.'''
        self.window = window
        self.response = response
        self.clock = clock
        self.eyetracker = eyetracker
        return

    def __call__(self):
        '''
        Check for responses and flip the screen. If this is called often
        enough you will achieve sync with the screen refresh (assuming that
        your window method holds until the refresh).'''
        frametime = self.window()
        response, resptime = self.response()
        return response, resptime, frametime

class Experiment(object):
    '''
    Class for running a set of trials in some experiment.'''

    def __init__(self, conditions=[], preevent=None, postevent=None,
                 subject=None, context=None):
        '''
        Initialise an Experiment instance.

        Keyword arguments:
        conditions -- dict or list of Event-derived instances (including
            EventSeq).
        preevent -- An event-derived instance that is called before the
            main trial sequence with an endtime of numpy.inf. This instance
            should practically always be initialised with
            skiponresponse=True.
        postevent -- An event-derived instance that is called after the
            main trial sequence. Otherwise similar to preevent above.
        subject -- str for log file. Prompted if undefined.
        context -- str for log file. Prompted if undefined.
        '''
        self.conditions = conditions
        self.preevent = preevent
        self.postevent = postevent
        if not subject:
            subject = raw_input('subject: ')
        self.subject = subject
        if not context:
            context = raw_input('context: ')
        self.context = context
        self.session = numpy.datetime64(datetime.datetime.now())
        return

    def __call__(self, controller, conditionkeys, seqclass=event.EventSeqAbsTime):
        '''
        Run a sequence of trials of the experiment, and return panda
        dataframes corresponding to the main trial sequence and the output
        of any pre/post events.

        Arguments:
        controller -- a Controller instance
        conditionkeys -- a list of keys or indices into self.conditions,
            which defines the sequence of conditions over the run.
        seqclass -- class to use for creating the trial sequence. Use
            EventSeqRelTime if absolute timing is not possible (e.g.,
            self-timed events, synching to pulses).
        '''
        # unpack to a fixed sequence of conditions
        # note that we leave name blank so we don't risk overwriting the
        # condition names in nested EventSeq-derived instances
        sequence = seqclass([self.conditions[key] for key in conditionkeys],
                            name=None)
        # run preevent, zero the clock
        preevlog = None
        if self.preevent:
            preevlog, preresplog = self.preevent(controller, numpy.inf)
            preevlog['subject'] = self.subject
            preevlog['session'] = self.session
            preevlog['context'] = self.context
        controller.clock.start()
        # main sequence
        eventlog, resplog = sequence(controller)
        # possible post-flight
        postevlog = None
        if self.postevent:
            postevlog, postresplog = self.postevent(controller, numpy.inf)
            postevlog['subject'] = self.subject
            postevlog['session'] = self.session
            postevlog['context'] = self.context
        eventlog['subject'] = self.subject
        eventlog['session'] = self.session
        eventlog['context'] = self.context
        return eventlog, resplog, preevlog, preresplog, postevlog, postresplog

    @addcustomdict
    def to_sql(self, res, path, customdict=None): # pylint: disable=unused-argument
        '''
        Save data to SQL database with self.context as key. If self.context
        exists, we append.
        '''
        import sqlalchemy
        engine = sqlalchemy.create_engine('sqlite:///' + path)
        res.to_sql(self.context, engine, if_exists='append')
        return

    @addcustomdict
    def to_hdf(self, res, path, customdict=None): # pylint: disable=unused-argument

        '''
        Save data to HDF database with self.context as key. If the self.context
        field already exists, we append.
        '''
        res.to_hdf(path, self.context, append=True)
        return
