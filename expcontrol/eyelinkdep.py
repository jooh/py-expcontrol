'''Functionality for interfacing with an EyeLink (SR Research) eye tracker.
Assumes that their pylink package is on your path.'''
import time
import numpy
import pylink # pylint: disable=import-error

class EyeLinkTracker(object):
    '''
    Handle common eye tracker tasks with a somewhat more intuitive
    interface than stock pylink.
    '''
    def __init__(self, size=[1024, 768], calibscale=1., ip='100.1.1.1', \
                 bgcolor=[127, 127, 127], fgcolor=[255, 255, 255], \
                 targetdiameter=20, targethole=5, calibrationtype='HV9', \
                 calibrationpacing=.9, viewdistance=None, screenwidth=None):

        self.size = tuple(size)
        # connect to tracker and do initial config
        self.tracker = pylink.EyeLink(ip)
        self.eyeused = None
        # flush out any pending key presses and get back to offline mode in
        # case we crashed out while recording
        pylink.flushGetkeyQueue()
        self.tracker.setOfflineMode()
        self.fgcolor = fgcolor
        self.bgcolor = bgcolor
        self.targetdiameter = targetdiameter
        self.targethole = targethole
        # month, day, hour, minute.
        self.remotefilename = time.strftime('%m%d%H%M')
        self.tracker.openDataFile(self.remotefilename)
        self.calibsize = (numpy.array(self.size) * calibscale)
        calibarea = numpy.round(numpy.array(self.size) - self.calibsize)
        alldims = (calibarea[0], calibarea[1], self.calibsize[0],
                   self.calibsize[1])
        self.tracker.sendCommand('screen_pixel_coords =  %d %d %d %d' % alldims)
        self.tracker.sendMessage("DISPLAY_COORDS  %d %d %d %d" % alldims)
        self.tracker.sendMessage("SCREEN_COORDS  0 0 %d %d" % self.size)
        # for robustness we set a bunch of other parameters so that any
        # weird defaults get overwritten
        if viewdistance:
            self.tracker.sendCommand('simulation_screen_distance=%d' % \
                                     (viewdistance * 10))
            self.tracker.sendMessage('VIEW_DISTANCE %d' % (viewdistance * 10))
        self.tracker.sendCommand('automatic_calibration_pacing=%d' % \
                                 (calibrationpacing * 1000))
        if screenwidth:
            self.tracker.sendMessage('SCREEN_WIDTH %d' % screenwidth)
        # NB this command is necessary whenever changing
        # screen_pixel_coords
        self.tracker.sendCommand('calibration_type=' + calibrationtype)
        if self.tracker.getTrackerVersion() == 2:
            self.tracker.sendCommand("select_parser_configuration 0")
        else:
            self.tracker.sendCommand("saccade_velocity_threshold = 35")
            self.tracker.sendCommand("saccade_acceleration_threshold = 9500")
            self.tracker.setFileEventFilter("LEFT,RIGHT,FIXATION,SACCADE,BLINK,MESSAGE,BUTTON")
            self.tracker.setFileSampleFilter("LEFT,RIGHT,GAZE,AREA,GAZERES,STATUS")
            self.tracker.setLinkEventFilter("LEFT,RIGHT,FIXATION,SACCADE,BLINK,BUTTON")
            self.tracker.setLinkSampleFilter("LEFT,RIGHT,GAZE,GAZERES,AREA,STATUS")
            self.tracker.sendCommand("button_function 5 'accept_target_fixation'")
        return

    def calibrate(self):
        '''
        Open a pygame window, run a calibration routine and close it.
        '''
        # start the main calibration/validation interface
        pylink.openGraphics(self.size)
        # these commands cause a hard crash if sent before openGraphics
        pylink.setCalibrationColors(self.fgcolor, self.bgcolor)
        pylink.setTargetSize(self.targetdiameter, self.targethole)
        self.tracker.doTrackerSetup()
        self.eyeused = self.tracker.eyeAvailable()
        pylink.closeGraphics()
        return

    def start(self):
        '''
        start recording eye tracking data.
        '''
        err = self.tracker.startRecording(1, 1, 1, 1)
        assert not err, 'EyeLink error: ' + err
        return

    def message(self, msg):
        '''
        send the str msg to the eye tracker.
        '''
        self.tracker.sendMessage(msg)
        return

    def stop(self, outfile):
        '''
        stop recording and receive the data file if outfile is not None.
        '''

        # pumpDelay is a lower priority delay which does not block background
        # events. msecDelay is more aggressive. Here used to catch last bit of
        # data before stopping the recording
        pylink.pumpDelay(100)
        # idle mode
        self.tracker.setOfflineMode()
        pylink.msecDelay(500)
        # close the file on the tracker HD. Can take a while...
        self.tracker.closeDataFile()
        if outfile is not None:
            self.tracker.receiveDataFile(self.remotefilename, outfile)
        self.tracker.close()
        return
