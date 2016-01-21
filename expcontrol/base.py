import numpy 
import datetime
import sqlalchemy
from . import event

class Controller(object):
    '''
    Control experiment timing, stimulus delivery and response collection.
    '''

    def __init__(self,window=None,response=None,clock=None):
        '''
        Initialise a controller instance. For example inputs, see
        expcontrol.psychopydep.window, KeyboardResponse and clock.'''
        self.window = window
        self.response = response
        self.clock = clock
        return

    def __call__(self):
        '''
        check for responses and flip the screen. If this is called often
        enough you will achieve sync with the screen refresh (assuming that
        your window method holds until the refresh).'''
        response = self.response()
        frametime = self.window()
        return response,frametime

class Experiment(object):
    '''
    Class for running a set of trials in some experiment.'''

    def __init__(self,conditions={},preevent=None,postevent=None,
            subject=None,context=None):
        '''
        Initialise an Experiment instance.

        Keyword arguments:
        conditions -- dict of Event-derived instances (including
            FixedEventSeq).
        preevent -- An event-derived instance that is called before the
            main trial sequence with an endtime of numpy.inf. This instance
            should practically always be initialised with
            skiponresponse=True.  postevent -- An event-derived instance
            that is called after the main trial sequence. Otherwise similar
            to preevent above.
        subject -- str for log file. Prompted if undefined.
        context -- str for log file. Prompted if undefined.'''
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

    def __call__(self,controller,conditionkeys):
        '''
        Run a sequence of trials of the experiment, and return panda
        dataframes corresponding to the main trial sequence and the output
        of any pre/post events.

        Arguments:
        controller -- a Controller instance
        conditionkeys -- a list of keys into self.conditions, which defines
            the sequence of conditions over the run.'''
        # unpack to a fixed sequence of conditions
        # note that we leave name blank so we don't risk overwriting the
        # condition names in nested FixedEventSeq instances
        sequence = event.FixedEventSeq(None,
                [self.conditions[key] for key in conditionkeys])
        # run preevent, zero the clock
        preres = None
        if self.preevent:
            preres = self.preevent(controller,numpy.inf)
            preres['subject'] = self.subject
            preres['session'] = self.session
            preres['context'] = self.context
        controller.clock.start()
        # main sequence
        res = sequence(controller)
        # possible post-flight
        postres = None
        if self.postevent:
            postres = self.postevent(controller,numpy.inf)
            postres['subject'] = self.subject
            postres['session'] = self.session
            postres['context'] = self.context
        res['subject'] = self.subject
        res['session'] = self.session
        res['context'] = self.context
        return res,preres,postres

    def save(self,res,path,customdict=None):
        engine = sqlalchemy.create_engine('sqlite:///' + path)
        if customdict:
            res = res.copy()
            for k,v in customdict.iteritems():
                res[k] = v
        res.to_sql(self.context,engine,if_exists='append')
        return
