import numpy
import pandas

eventkeys = ['name','condition','oncall','onframe','onresponse','onend',
            'response_key','response_time']

class Event(object):
    '''
    The smallest independent element of an experiment. This class stubs out
    callbacks for different stages of the Event (oncall, onframe,
    onresponse, onend). The purpose of this is to support sub-classing
    where only some of these methods may be required, and to demonstrate
    the input syntax required by the call method.'''

    def __init__(self,name=None,duration=None,skiponresponse=False):
        '''
        Initialise an Event instance.
        
        Keyword arguments:
        name --- is placed in the name field of the return from the call
            method.
        duration --- length of event in controller.clock units. Note that
            the duration field is not used directly here in this class, but
            is referenced elsewhere to set the endtime argument correctly
            at calltime.  skiponresponse -- if skiponresponse, the Event is
            terminated early when a response is detected. This can be
            useful in conjunction with duration=numpy.inf in e.g.
            Experiment.precondition to present instructions until the
            subject is ready to start.'''
        self.name = name
        self.duration = duration
        self.skiponresponse = skiponresponse
        super(Event,self).__init__()
        return

    def __call__(self,controller=None,endtime=None,currentres=None):
        '''
        Run the event through once and return a pandas DataFrame with a
        single row and columns for the output of each Event callback (see
        eventkeys).
        
        Keyword arguments:
        controller -- a Controller instance
        endtime -- the trial end in controller.clock units 
        currentres -- this variable is passed on to each callback function
            and can be used for e.g. response scoring. It can be
            constructed conveniently by concatenating return values of
            previous trials (see FixedEventSeq).'''
        res = pandas.DataFrame(columns=eventkeys,
                index=[controller.clock()],dtype=float)
        res['name'] = self.name
        res['oncall'] = self.oncall(controller,currentres)
        skipahead = False
        while controller.clock() < endtime and not skipahead:
            res['onframe'] = self.onframe(controller,currentres)
            response,frametime = controller();
            if response:
                res['response_key'] = response[0]
                res['response_time'] = controller.clock()
                res['onresponse'] = self.onresponse(controller,
                        res.iloc[0]['response_key'],
                        res.iloc[0]['response_time'],
                        currentres)
                if self.skiponresponse:
                    skipahead = True
        res['onend'] = self.onend(controller,currentres)
        return res

    def oncall(self,controller,currentres,*args,**kwargs):
        '''This method is called at the beginning of the event.'''
        pass

    def onframe(self,controller,currentres,*args,**kwargs):
        '''This method is called on the frame refresh.'''
        pass

    def onresponse(self,controller,response,rt,currentres):
        '''This method is called when the controller detects a response.'''
        return numpy.nan

    def onend(self,controller,currentres,*args,**kwargs):
        '''This method is called at the end of the event.'''
        pass

class FixedEventSeq(Event):
    '''
    Class for running through a fixed sequence of Event instances.  Useful
    for defining conditions in complex designs, where your events might
    reflect stimulus, response, feedback and iti phases. In principle it is
    possible to run an entire experiment by specifying a long enough
    sequence in this instance, but in practice Experiment is a better bet
    for this.''' 

    def __init__(self,name=None,events=[],duration=None):
        '''
        Initialise a FixedEventSeq instance.

        Keyword arguments:
        name -- is placed in the condition field in the res field generated
            on call.
        events -- list of Event instances. Note that these can be
            FixedEventSeq instances to easily generate complex sequences
            (but note that if you use this functionality you want to set
            the name field to None in all but one recursion level, since
            all levels will write to the same condition field in the call
            return (and the outermost will be the last one in).
        duration -- duration of entire sequence in controller.clock units.
            If undefined the duration is inferred from the sum of the event
            durations. It can be useful to set the duration to a slightly
            larger value than this to correct for lag.'''
        super(FixedEventSeq,self).__init__(name=name,duration=duration,
                skiponresponse=False)
        self.events = events
        durations = numpy.array([x.duration for x in self.events])
        self.endtimes = numpy.cumsum(durations)
        realdur = numpy.sum(durations)
        if not self.duration:
            # infer duration from sum of event durations
            # (note that by setting a duration > than the sum, you can
            # achieve a bit of catchup time to get around lag issues)
            self.duration = realdur
        assert numpy.isinf(self.duration) or self.duration >= realdur, \
                'event duration cannot exceed condition duration'
        return

    def __call__(self,controller=None,endtime=0.,currentres=None):
        '''
        Run through the sequence of events. Similar call syntax as Event.
        '''
        starttime = controller.clock()
        endtimes_trial = starttime + self.endtimes
        # nb, we ignore currentres
        newres = pandas.DataFrame(columns=eventkeys,dtype=float)
        for ind,ev in enumerate(self.events):
            newres = pandas.concat([newres,ev(controller=controller,
                endtime=endtimes_trial[ind],currentres=newres)],
                axis=0)
        if self.name:
            # the additional if statement here is useful to control when
            # existing condition fields get over-written (generally you
            # want that to happen at the condition level, but not at the
            # experiment level since you'd end up with a single label for
            # all events).
            newres['condition'] = self.name
        # potential catchup phase
        while controller.clock() < endtime:
            controller()
        # return start and end time for debugging purposes
        return newres

class DrawEvent(Event):
    '''
    Event sub-class for handling a set of drawinstance, each of which have
    a draw() method that is called in turn on the frame rate. This is
    useful for visual presentation based on e.g. Psychopy.visual instances. 
    '''

    def __init__(self,drawinstances=[],**kwargs):
        '''
        Initialise a DrawEvent instance. The input drawinstances is a list
        of instances that have a draw method which takes no input
        arguments. Any remaining arguments are passed to Event.'''
        super(DrawEvent,self).__init__(**kwargs)
        if type(drawinstances) is not list:
            drawinstances = [drawinstances]
        self.drawinstances = drawinstances
        return

    def onframe(self,controller,currentres):
        '''
        Callback for drawing the drawinstances to the screen. Usually
        referenced from the call method of Event.

        Arguments:
        controller -- a Controller instance
        currentres -- a result table (not actually used here but preserved
            for potential subclassing)'''
        [x.draw() for x in self.drawinstances]
        return

class RespEvent(DrawEvent):
    '''
    DrawEvent sub-class for handling a combination of drawing stimuli to
    the screen (see DrawEvent) and collecting responses.'''

    def __init__(self,drawinstances=[],correct=None,minrt=0.,**kwargs):
        '''
        Initialise a RespEvent instance and configure accuracy-based
        scoring.

        Arguments:
        drawinstances -- see DrawEvent
        correct=None -- list of keys to be scored as correct
        minrt=0. -- minimum reaction time in controller.clock units for
            valid responses (quicker responses are ignored).
        kwargs -- any additional arguments are passed to Event.'''
        super(RespEvent,self).__init__(drawinstances=drawinstances,**kwargs)
        self.starttime = numpy.nan
        if type(correct) is not list:
            correct = [correct]
        self.correct = correct
        self.minrt = minrt
        return

    def oncall(self,controller,res):
        '''
        callback for RespEvent. The main functionality here is to reset the
        starttime property which is used for calculating reaction times.
        
        Arguments:
        controller -- Controller instance
        res -- not used here.
        '''
        # reset the scoring at trial start
        self.starttime = controller.clock()
        return

    def onresponse(self,controller,response,rt,currentres):
        '''
        callback for RespEvent. Provides basic accuracy-based scoring of
        responses.

        Arguments:
        controller -- Controller instance
        response -- list of inputs
        rt -- reaction times in absolute time units (controller.clock units)
        currentres -- not used here.'''
        if (rt-self.starttime) < self.minrt:
            # ignore scoring of anticipations
            return numpy.nan
        outacc = False
        if response in self.correct:
            outacc = True
        return outacc
