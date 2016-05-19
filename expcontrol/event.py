'''Event and event sequence handling for expcontrol.'''
import numpy
import pandas

EVENTKEYS = ['name', 'condition', 'oncall', 'onframe', 'onend']

def prepeventrow(ind=None):
    '''
    return row(s) of the event log with columns as in eventkeys and indices
    as in ind.
    '''
    return pandas.DataFrame(columns=EVENTKEYS, index=ind, dtype=float)

RESPKEYS = ['key', 'onresponse_score', 'onresponse_rt']

def prepresprow(ind=None):
    '''
    return row(s) of the response log with columns as in respkey and indices
    as in ind.
    '''
    return pandas.DataFrame(columns=RESPKEYS, index=ind, dtype=float)

class Event(object):
    '''
    The smallest independent element of an experiment. This class stubs out
    callbacks for different stages of the Event (oncall, onframe,
    onresponse, onend). The purpose of this is to support sub-classing
    where only some of these methods may be required.
    '''

    def __init__(self, name=None, duration=0, skiponresponse=[], verbose=False):
        '''
        Initialise an Event instance.

        Keyword arguments:
        name --- is placed in the name field of the return from the call method.
        duration --- length of event in controller.clock units. Note that the
            duration field is not used directly here in this class, but is
            referenced elsewhere to set the endtime argument correctly at
            calltime.
        skiponresponse -- if skiponresponse, the Event is terminated early
            when a response is detected. This can be useful in conjunction
            with duration=numpy.inf in e.g. Experiment.precondition to
            present instructions until the subject is ready to start.
        verbose=False -- Print to console as we go.
        '''
        super(Event, self).__init__()
        self.name = name
        self.duration = duration
        self.verbose = verbose
        self.skiponresponse = []
        self.setaslist('skiponresponse', skiponresponse)
        return

    def setaslist(self, name, val):
        '''
        Utility method for constraining an input val to list type before
        assigning as attribute name.
        '''
        try:
            setattr(self, name, list(val))
        except TypeError:
            setattr(self, name, [val])
        except:
            raise
        return

    def __call__(self, controller, endtime, currentevlog=None, currentresplog=None):
        '''
        Run the event through once and return pandas DataFrames with event
        and response logs.

        Keyword arguments:
        controller -- a Controller instance
        endtime -- the trial end in controller.clock units
        currentevlog -- this variable is passed on to each callback function
            and can be used for e.g. response scoring. It can be constructed
            conveniently by concatenating eventlogs from previous trials (see
            EventSeq). We assume that each event is a single row in this log.
        currentresplog -- similar to evlog above, but one row per response
            rather than per event.

        Returns (both indexed by controller.clock()):
        eventlog -- pandas.DataFrame with 1 row. Columns contain the
            result of each callback (see event.EVENTKEYS).
        resplog -- pandas.Series with one entry per key press.
        '''
        eventlog = prepeventrow([controller.clock()])
        eventlog['name'] = self.name
        eventlog['oncall'] = self.oncall(controller, currentevlog,
                                         currentresplog)
        if controller.eyetracker:
            controller.eyetracker.message(self.name)
        skipahead = False
        resplog = prepresprow()
        while controller.clock() < endtime and not skipahead:
            eventlog['onframe'] = self.onframe(controller, currentevlog,
                                               currentresplog)
            response, resptime, frametime = controller()
            if len(response):
                thisresp = prepresprow(ind=resptime)
                thisresp['key'] = response
                thisresp['onresponse_score'], thisresp['onresponse_rt'] = \
                        self.onresponse(controller, response, resptime,
                                        currentevlog, currentresplog)
                resplog = pandas.concat([resplog, thisresp], axis=0) # pylint: disable=redefined-variable-type
                if numpy.any(numpy.in1d(response, self.skiponresponse)):
                    skipahead = True
        eventlog['onend'] = self.onend(controller, currentevlog, currentresplog)
        if self.verbose:
            print eventlog.to_string(header=False)
        return eventlog, resplog

    def oncall(self, controller, currentevlog, currentresplog):
        '''This method is called at the beginning of the event.'''
        pass

    def onframe(self, controller, currentevlog, currentresplog):
        '''This method is called on the frame refresh.'''
        pass

    def onresponse(self, controller, response, rt, currentevlog, currentresplog):
        '''This method is called when a response is detected.'''
        nullresp = numpy.empty(numpy.shape(response))
        nullresp.fill(numpy.nan)
        return nullresp, nullresp

    def onend(self, controller, currentevlog, currentresplog):
        '''This method is called at the end of the event.'''
        pass

class EventSeq(Event):
    '''
    Base class for running through a fixed sequence of Event instances.
    Useful for defining conditions in complex designs, where your events
    might reflect stimulus, response, feedback and iti phases. In principle
    it is possible to run an entire experiment by specifying a long enough
    sequence in this instance, but in practice Experiment is a better bet
    for this. Direct use of this class is not supported - use the
    EventSeqRelTime and EventSeqAbsTime sub-classes.
    '''

    def __init__(self, events=[], **kwargs):
        '''
        Initialise a EventSeq instance.

        Keyword arguments:
        name -- is placed in the condition field in the res field generated on
            call.
        events -- list of Event instances. Note that these can be EventSeq
            instances to easily generate complex sequences (but note that if you
            use this functionality you want to set the name field to None in all
            but one recursion level, since all levels will write to the same
            condition field in the call return (and the outermost will be the
            last one in).
        duration -- duration of entire sequence in controller.clock units. If
            undefined the duration is inferred from the sum of the event
            durations. It can be useful to set the duration to a slightly larger
            value than this to correct for lag.
        verbose=False -- Print to console as we go.
        '''
        super(EventSeq, self).__init__(**kwargs)
        self.events = events
        self.eventdur = numpy.array([thisev.duration for thisev in self.events])
        self.eventskip = [not len(thisev.skiponresponse) for thisev in
                          self.events]
        return

    def __call__(self, controller, endtime=0., currentevlog=None, currentresplog=None):
        '''
        do not use. This is for subclass use only.
        '''
        if self.name:
            # the additional if statement here is useful to control when
            # existing condition fields get over-written (generally you want
            # that to happen at the condition level, but not at the experiment
            # level since you'd end up with a single label for all events).
            currentevlog['condition'] = self.name
        # potential catchup phase
        controller.clock.waituntil(endtime)
        return currentevlog

class EventSeqRelTime(EventSeq):
    '''
    EventSeq subclass for relative timings. Useful for cases where absolute
    timing relative to experiment start is impossible (e.g., self timed
    tasks, synching to scanner pulses).
    '''
    def __init__(self, *args, **kwargs):
        super(EventSeqRelTime, self).__init__(*args, **kwargs)
        self.timing = self.eventdur
        assert not self.duration, \
            'cannot set EventSeq duration with relative timings'
        return

    def __call__(self, controller=None, endtime=0., currentevlog=None, currentresplog=None):
        outevlog = prepeventrow()
        outresplog = prepresprow()
        for ind, thisevent in enumerate(self.events):
            # get time on every trial
            currenttime = controller.clock()
            thisevlog, thisresp = thisevent(controller,
                                            currenttime+self.timing[ind],
                                            currentevlog, currentresplog)
            # NB we append the full log, but do not return this to avoid
            # duplicates with nested calls
            currentevlog = pandas.concat([currentevlog, thisevlog], axis=0)
            currentresplog = pandas.concat([currentresplog, thisresp], axis=0)
            outevlog = pandas.concat([outevlog, thisevlog], axis=0)
            outresplog = pandas.concat([outresplog, thisresp], axis=0)
            if self.verbose:
                print '%.1f\t %s' % (currenttime, thisevent.name)
        return super(EventSeqRelTime, self).__call__(controller, endtime, outevlog), outresplog

class EventSeqAbsTime(EventSeq):
    '''
    EventSeq subclass for absolute timings. Given reasonable inputs this
    class will guarantee non-slip time over the course of the run.
    '''
    def __init__(self, *args, **kwargs):
        super(EventSeqAbsTime, self).__init__(*args, **kwargs)
        self.timing = numpy.cumsum(self.eventdur)
        realdur = numpy.sum(self.eventdur)
        if not self.duration:
            # infer duration from sum of eventdur
            # (note that by setting a duration > than the sum, you can achieve a
            # bit of catchup time to get around lag issues)
            self.duration = realdur
        assert numpy.isinf(self.duration) or self.duration >= realdur, \
                'event duration cannot exceed condition duration'
        assert not numpy.any(numpy.isinf(self.eventdur) | self.eventskip),\
                'EventSeqAbsTime is not supported for these events'
        return

    def __call__(self, controller, endtime=0., currentevlog=None, currentresplog=None):
        starttime = controller.clock()
        evlog = prepeventrow()
        resplog = prepresprow()
        endtimes_trial = starttime + self.timing
        for ind, thisevent in enumerate(self.events):
            thisevlog, thisresp = thisevent(controller, endtimes_trial[ind],
                                            currentevlog, currentresplog)
            evlog = pandas.concat([evlog, thisevlog], axis=0)
            resplog = pandas.concat([resplog, thisresp], axis=0)
            # NB we append the full log, but do not return this to avoid
            # duplicates with nested calls
            currentevlog = pandas.concat([currentevlog, thisevlog], axis=0)
            currentresplog = pandas.concat([currentresplog, thisresp], axis=0)
        return super(EventSeqAbsTime, self).__call__(controller, endtime, evlog), resplog

class DrawEvent(Event):
    '''
    Event sub-class for handling a set of drawinstance, each of which have a
    draw() method that is called in turn on the frame rate. This is useful for
    visual presentation based on e.g. Psychopy.visual instances.
    '''

    def __init__(self, drawinstances, **kwargs):
        '''
        Initialise a DrawEvent instance. The input drawinstances is a list of
        instances that have a draw method which takes no input arguments. Any
        remaining arguments are passed to Event.
        '''
        super(DrawEvent, self).__init__(**kwargs)
        self.drawinstances = []
        self.setaslist('drawinstances', drawinstances)

    def onframe(self, controller, currentevlog, currentresplog):
        '''
        Callback for drawing the drawinstances to the screen. Usually referenced
        from the call method of Event.

        Arguments:
        controller -- a Controller instance
        currentevlog -- a result table (not actually used here but preserved
            for potential subclassing).
        currentresplog -- current responses.
        '''
        [x.draw() for x in self.drawinstances]
        return

class FeedbackEvent(DrawEvent):
    '''
    Provide feedback to the subject by plugging currentevlog and currentresplog
    into some scorer handle, and drawing different stimuli to the screen as a
    function of its return value.
    '''

    def __init__(self, drawinstances, scorer, correctdraw=[], incorrectdraw=[],\
                 omitdraw=[], **kwargs):
        super(FeedbackEvent, self).__init__(drawinstances, **kwargs)
        self.scorer = scorer
        # nb slice to ensure copy
        self.commondraw = []
        self.setaslist('commondraw', self.drawinstances[:])
        self.correctdraw = []
        self.setaslist('correctdraw', correctdraw)
        self.incorrectdraw = []
        self.setaslist('incorrectdraw', incorrectdraw)
        self.omitdraw = []
        self.setaslist('omitdraw', omitdraw)
        return

    def oncall(self, controller, currentevlog, currentresplog):
        super(FeedbackEvent, self).oncall(controller, currentevlog,
                                          currentresplog)
        thisscore = self.scorer(currentevlog, currentresplog)
        # ensure copy
        self.drawinstances = self.commondraw[:]
        if pandas.isnull(thisscore):
            self.drawinstances += self.omitdraw
        elif thisscore == 1:
            self.drawinstances += self.correctdraw
        else:
            self.drawinstances += self.incorrectdraw
        return thisscore

class DetectionEvent(DrawEvent):
    '''
    DrawEvent subclass for handling response scoring in simple detection tasks.
    '''

    def __init__(self, drawinstances, correct=None, minrt=0., **kwargs):
        super(DetectionEvent, self).__init__(drawinstances, **kwargs)
        self.starttime = numpy.nan
        self.correct = []
        self.setaslist('correct', correct)
        assert '*' not in self.correct, '* is a reserved character'
        self.minrt = minrt
        return

    def oncall(self, controller, currentevent, currentresp):
        '''
        callback for DetectionEvent. The main functionality here is to reset the
        starttime property which can be used for calculating reaction times.

        Arguments:
        controller -- Controller instance
        currentevent -- not used here.
        currentresp -- not used here.
        '''
        # reset the timing at trial start
        super(DetectionEvent, self).oncall(controller, currentevent,
                                           currentresp)
        self.starttime = controller.clock()
        return

    def preparescore(self, response, resptime):
        '''
        handle basic input filtering: convert raw response time to RT, rescore
        anticipations as invalid. Typically used internally in onresponse
        callbacks.
        '''
        rt = resptime - self.starttime
        # filter anticipations
        antind = rt < self.minrt
        rt[antind] = numpy.nan
        # can't use nan with char arrays
        response[antind] = '*'
        return response, rt

    def onresponse(self, controller, response, resptime, currentevlog, currentresplog):
        '''
        onresponse callback for DetectionEvent. Returns 1 for correct detections
        and nans for other responses.
        '''
        response, rt = self.preparescore(response, resptime)
        wascorrect = numpy.empty(numpy.shape(rt))
        wascorrect.fill(numpy.nan)
        wascorrect[numpy.in1d(response, self.correct)] = 1
        rt[numpy.isnan(wascorrect)] = numpy.nan
        return wascorrect, rt

class DecisionEvent(DetectionEvent):
    '''
    DetectionEvent sub-class for handling a combination of drawing stimuli to
    the screen (see DrawEvent) and collecting responses.
    '''

    def __init__(self, drawinstances, incorrect=None, **kwargs):
        '''
        Initialise a DecisionEvent instance and configure accuracy-based
        scoring.

        Arguments:
        drawinstances -- see DrawEvent
        correct=None -- list of keys to be scored as correct
        incorrect=None -- list of keys to be scored as incorrect
        minrt=0. -- minimum reaction time in controller.clock units for
            valid responses (quicker responses are ignored).
        kwargs -- any additional arguments are passed to Event.'''
        super(DecisionEvent, self).__init__(drawinstances, **kwargs)
        self.incorrect = []
        self.setaslist('incorrect', incorrect)
        assert '*' not in self.incorrect, '* is a reserved character'
        return

    def onresponse(self, controller, response, responsetime, currentevlog, currentresplog):
        '''
        onresponse callback for DecisionEvent. Provides basic accuracy-based
        scoring of responses.

        Arguments:
        controller -- Controller instance
        response -- list of inputs
        responsetime -- reaction times in absolute time units (controller.clock units)
        currentevlog -- not used here.
        currentresplog -- not used here.
        '''
        response, rt = self.preparescore(response, responsetime)
        wascorrect = numpy.empty(numpy.shape(rt))
        wascorrect.fill(numpy.nan)
        wascorrect[numpy.in1d(response, self.incorrect)] = 0
        wascorrect[numpy.in1d(response, self.correct)] = 1
        rt[wascorrect != 1] = numpy.nan
        if self.verbose:
            print 'correct=%s\tkey=%s' % (wascorrect, response)
        return wascorrect, rt

class NBackEvent(DecisionEvent):
    '''
    DecisionEvent subclass for scoring of Nback repetition detection tasks.
    '''
    def __init__(self, drawinstances, nback=1, nshift=0, **kwargs):
        super(NBackEvent, self).__init__(drawinstances, **kwargs)
        self.nback = nback
        # makes it possible to score e.g. an isi according to the previous
        # stimulus by shifting the whole scoring scheme a step backwards
        self.nshift = nshift
        self.wasrep = numpy.nan
        self.repkey = self.correct[:]
        self.notrepkey = self.incorrect[:]
        return

    def oncall(self, controller, currentevlog, currentresplog):
        # important to super here to reset starttime
        super(NBackEvent, self).oncall(controller, currentevlog, currentresplog)
        if self.nshift == 0:
            currentname = self.name
        else:
            try:
                currentname = currentevlog.iloc[self.nshift]['name']
            except IndexError:
                currentname = numpy.nan
            except:
                raise
        try:
            previousname = currentevlog.iloc[self.nshift-self.nback]['name']
        except IndexError:
            previousname = numpy.nan
        except:
            raise
        self.wasrep = 0.
        if pandas.isnull(currentname) or pandas.isnull(previousname):
            self.wasrep = numpy.nan
        elif currentname == previousname:
            self.wasrep = 1.
        if self.verbose:
            print 'current=%s\t last=%s\twasrep=%s' % \
                    (currentname, previousname, self.wasrep)
        # so now we just reassign the keys
        if self.wasrep:
            self.correct = self.repkey[:]
            self.incorrect = self.notrepkey[:]
        else:
            self.correct = self.notrepkey[:]
            self.incorrect = self.repkey[:]
        return

class SynchEvent(DetectionEvent):
    '''
    DetectionEvent subclass for synchronising with the scanner. The typical use
    is to drop this instance in toward the end of a trial in a EventSeqRelTime
    sequence in order to trigger the next trial on the volume pulse.
    '''
    def __init__(self, drawinstances, targetkey, duration=numpy.inf, name='synch', **kwargs):
        super(SynchEvent, self).__init__(drawinstances, correct=targetkey,
                                         skiponresponse=targetkey,
                                         duration=duration, name=name, **kwargs)
        return

    def oncall(self, controller, currentevlog, currentresplog):
        '''
        oncall callback for SynchEvent. Only used for logging functionality.
        '''
        super(SynchEvent, self).oncall(controller, currentevlog, currentresplog)
        if self.verbose:
            print 'waiting for pulse...'
        return

    def onresponse(self, controller, response, resptime, currentevlog, currentresplog):
        '''
        onresponse callback for SynchEvent. Returns 1 for detected pulses and
        nan for any other responses. Note that the second return provides
        response time in absolute units rather than normalised by event start.
        '''
        # nb we don't want to score RT of pulse for obvious reasons..
        response, null = self.preparescore(response, resptime)
        waspulse = numpy.empty(numpy.shape(null))
        waspulse.fill(numpy.nan)
        waspulse[numpy.in1d(response, self.correct)] = 1.
        resptime[numpy.isnan(waspulse)] = numpy.nan
        return waspulse, resptime
