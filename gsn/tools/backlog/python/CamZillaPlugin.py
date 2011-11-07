#! /usr/bin/python
# -*- coding: UTF-8 -*-
__author__      = "Tonio Gsell <tgsell@tik.ee.ethz.ch>"
__copyright__   = "Copyright 2010, ETH Zurich, Switzerland, Tonio Gsell"
__license__     = "GPL"
__version__     = "$Revision$"
__date__        = "$Date$"
__id__          = "$Id$"
__source__      = "$URL$"

import logging
import Queue
import os
import time
import thread
from threading import Thread, Event, Lock

from ScheduleHandler import SUBPROCESS_BUG_BYPASS
if SUBPROCESS_BUG_BYPASS:
    import SubprocessFake
    subprocess = SubprocessFake
else:
    import subprocess

import BackLogMessage
from AbstractPlugin import AbstractPluginClass

try: 
    import serial
except ImportError, e: 
    print "Please install PySerial first."
    sys.exit(1)

DEFAULT_BACKLOG = True
GPHOTO2 = '/usr/bin/gphoto2'
PICTUREFOLDER = '/media/card/backlog/binaryplugin/camera1/'
POSTFIX='.%C'
DEFAULT_GPHOTO2_SETTINGS = ['/main/settings/capturetarget=1','/main/imgsettings/imagequality=0','/main/imgsettings/imagesize=2']

TASK_MESSAGE = 0
POWER_MESSAGE = 1

PANORAMA_TASK = 0
PICTURE_TASK = 1
POSITIONING_TASK = 2
MODE_TASK = 3
CALIBRATION_TASK = 4

class CamZillaPluginClass(AbstractPluginClass):
    '''
    This plugin offers the functionality to control the CamZilla robot.
    '''

    '''
    data/instance attributes:
    _manualControl
    _delay
    _writeLock
    _xMaxRotation
    _xRotationToPulse
    _yMaxRotation
    _yRotationToPulse
    _taskqueue
    _plugStop
    _isBusy
    '''
    
    def __init__(self, parent, config):
        AbstractPluginClass.__init__(self, parent, config, DEFAULT_BACKLOG, needPowerControl=True)
        self._isBusy = True
        
        self._serial = serial.Serial()
        self._taskqueue = Queue.Queue()
        self._delay = Event()
        self._writeLock = Lock()
        self._manualControl = True
        self._plugStop = False
        self._power = False
        self._x = None
        self._y = None
        
        device = self.getOptionValue('device_name')
        if device is None:
            raise TypeError('no device_name specified')
        
        value = self.getOptionValue('max_horizontal_rotation')
        if value is None:
            raise TypeError('no max_horizontal_rotation value specified')
        else:
            self._xMaxRotation = int(value)
        
        value = self.getOptionValue('max_vertical_rotation')
        if value is None:
            raise TypeError('no max_vertical_rotation value specified')
        else:
            self._yMaxRotation = int(value)
            
        self.info('maximum possible robot rotation in degrees: x=%d, y=%d' % (self._xMaxRotation,self._yMaxRotation))
        self.info('using device %s' % (device,))
        self._serial.setPort(device)
        
        if not os.path.isdir(PICTUREFOLDER):
            self.warning('picture folder >%s< is not a directory -> creating it' % (PICTUREFOLDER,))
            os.makedirs(PICTUREFOLDER)
            
        if not os.path.exists(GPHOTO2):
            raise TypeError('%s does not exist' % (GPHOTO2,))
        if not os.access(GPHOTO2, os.X_OK):
            raise TypeError('%s can not be executed' % (GPHOTO2,))
        
        if self.getPowerControlObject().getUsb3Status():
            self.info('USB3 port is turned on')
        else:
            self.info('USB3 port is turned off')
        
        if self.getPowerControlObject().getExt1Status():
            self.info('robot and photo camera is turned on')
        else:
            self.info('robot and photo camera is turned off')
        
        value = self.getOptionValue('power_save_mode')
        self._powerSaveMode = False
        if value != None and int(value) == 1:
            self.info('power save mode is turned on')
            self._powerSaveMode = True
        else:
            self.info('power save mode is turned off')
            self._startupRobotAndCam()
    
    
    def getMsgType(self):
        return BackLogMessage.CAMZILLA_MESSAGE_TYPE
        
        
    def isBusy(self):
        return self._isBusy
        
        
    def needsWLAN(self):
        return False
    
    
    def msgReceived(self, data):
        try:
            thread.start_new_thread(self._parseMsg, (data,))
        except Exception, e:
            self.exception(e)
       
        
    def run(self):
        self.name = 'CamZillaPlugin-Thread'
        self.info('started')
        
        if not self._powerSaveMode:
            self._calibrateRobot()

        while not self._plugStop:
            if self._taskqueue.empty():
                self._isBusy = False
            task = self._taskqueue.get()
            self._isBusy = True
            if self._plugStop:
                try:
                    self._taskqueue.task_done()
                except ValueError, e:
                    self.exception(e)
                break
            
            try:
                now = time.time()
                if task[0] == PANORAMA_TASK:
                    parsedTask = self._parseTask(task[1])
                    
                    if self._powerSaveMode:
                        self._startupRobotAndCam()
                        self._calibrateRobot()
                    
                    self.info('executing panorama picture task: start(%s,%s) pictures(%s,%s) rotation(%s,%s) delay(%s) gphoto2(%s)' % (str(parsedTask[0]), str(parsedTask[1]), str(parsedTask[2]), str(parsedTask[3]), str(parsedTask[4]), str(parsedTask[5]), str(parsedTask[6]), str(parsedTask[7])))
                
                    if self._power:
                        pic = 1
                        try:
                            y = parsedTask[1]
                            while y < parsedTask[1]+(parsedTask[3]*parsedTask[5]):
                                self._position(y=y)
                                x = parsedTask[0]
                                while x < parsedTask[0]+(parsedTask[2]*parsedTask[4]):
                                    self._position(x=x)
                                    if self._plugStop:
                                        break
                                    if parsedTask[6] > 0:
                                        self._delay.wait(parsedTask[6])

                                    self.info('taking picture number %d/%d at position (%f,%f)' % (pic,parsedTask[2]*parsedTask[3],x,y))
                                    config = self._takePicture(parsedTask[7])
                                    self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['panorama', 'picture number %d/%d' % (pic,parsedTask[2]*parsedTask[3]), x, y] + parsedTask[:-1] + [config])
                                    pic += 1

                                    x += parsedTask[4]
                                if self._plugStop:
                                    break
                                y += parsedTask[3]
                        except Exception, e:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['panorama', 'could not finish task successfully (%s)' % (e.__str__(),), self._x, self._y] + parsedTask[:-1] + [config])
                            self.error(e.__str__())
                        else:
                            self.info('all pictures taken successfully')
                        
                            if not self._plugStop:
                                try:
                                    self._downloadPictures(time.strftime('%Y%m%d_%H%M%S', time.gmtime(now)))
                                except Exception, e:
                                    self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['panorama', 'could not download all pictures (%s)' % (e.__str__(),), self._x, self._y] + parsedTask[:-1] + [config])
                                    self.error(e.__str__())
                                else:
                                    self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['panorama', 'finished successfully', self._x, self._y] + parsedTask[:-1] + [config])
                                    self.info('panorama picture task finished successfully')
                        
                        if self._powerSaveMode:
                            self._shutdownRobotAndCam()
                    else:
                        self.error('robot is not powered -> can not execute command')
                elif task[0] == PICTURE_TASK:
                    self.info('picture now task received -> taking picture in current robot position now')
                    if task[1]:
                        gphoto2conf = task[1].split(',')
                    else:
                        gphoto2conf = []
                    try:
                        config = self._takePicture(gphoto2conf)
                    except Exception, e:
                        self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['picture_now', 'could not take picture now (%s)' % (e.__str__(),), self._x, self._y] + [None]*7 + [config])
                        self.error(e.__str__())
                    else:
                        try:
                            self._downloadPictures(time.strftime('%Y%m%d_%H%M%S', time.gmtime(now)))
                        except Exception, e:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['picture_now', 'could not download all pictures (%s)' % (e.__str__(),), self._x, self._y] + [None]*7 + [config])
                            self.error(e.__str__())
                        else:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['picture_now', 'finished successfully', self._x, self._y] + [None]*7 + [config])
                            self.info('picture now task finished successfully')
                elif task[0] == POSITIONING_TASK:
                    self.info('positioning task received (x=%f,y=%f)' % (task[1], task[2]))
                    if self._power:
                        try:
                            self._position(x=task[1], y=task[2])
                        except Exception, e:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['positioning', 'not finished successfully (%s)' % (e.__str__(),), self._x, self._y] + [None]*8)
                            self.error(e.__str__())
                        else:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['positioning', 'finished successfully', self._x, self._y] + [None]*8)
                            self.info('positioning task finished successfully')
                    else:
                        self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['positioning', 'CamZilla is not powered -> turn power on first', self._x, self._y] + [None]*8)
                        self.error('CamZilla has no power -> turn power on first')
                elif task[0] == MODE_TASK:
                    if self._power:
                        if not self._powerSaveMode:
                            if task[1] == 0:
                                self.info('mode task received from GSN >joystick off<')
                                self._write("j=off")
                                self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['mode', 'joystick turned off', self._x, self._y] + [None]*8)
                            elif task[1] == 1:
                                self.info('mode task received from GSN >joystick on<')
                                self._write("j=on")
                                self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['mode', 'joystick turned on', self._x, self._y] + [None]*8)
                            else:
                                self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['mode', 'unknown mode', self._x, self._y] + [None]*8)
                                self.error('unknown mode task received from GSN')
                        else:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['mode', 'BackLog is in power save mode -> do nothing', self._x, self._y] + [None]*8)
                            self.error('mode task received from GSN but in power save mode -> do nothing')
                    else:
                        self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['mode', 'CamZilla is not powered -> turn power on first', self._x, self._y] + [None]*8)
                        self.error('mode task received from GSN but robot not powered -> do nothing')
                elif task[0] == CALIBRATION_TASK:
                    if self._powerSaveMode:
                        self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['calibration', 'BackLog is in power save mode -> do nothing', self._x, self._y] + [None]*8)
                        self.info('calibration task received from GSN but in power save mode -> do nothing')
                    else:
                        if self._power:
                            self.info('calibration task received from GSN -> calibrate robot')
                        self._calibrateRobot()
                        if self._power:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['calibration', 'finished successfully', self._x, self._y] + [None]*8)
                        else:
                            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['calibration', 'CamZilla is not powered -> turn power on first', self._x, self._y] + [None]*8)
                        
            except Exception, e:
                self.exception(str(e))
                
            try:
                self._taskqueue.task_done()
            except ValueError, e:
                self.exception(e)
        
        self.info('died')


    def action(self, parameters):
        if isinstance(parameters, str):
            self._taskqueue.put([PANORAMA_TASK, parameters])
        else:
            self._taskqueue.put(parameters)
    
    
    def stop(self):
        self._isBusy = False
        self._plugStop = True
        self._taskqueue.put('end')
        self._delay.set()
        self._powerSaveMode = True
        self._shutdownRobotAndCam()
            
            
    def _parseMsg(self, data):
        if data[0] == TASK_MESSAGE:
            self.info('new task message received from GSN')
            self.action(data[1:])
        elif data[0] == POWER_MESSAGE:
            now = time.time()
            self.info('power message received from GSN')
            power = None
            if data[1] == 0:
                self.info('turn robot and camera off')
                if self._shutdownRobotAndCam():
                    power = False
            elif data[1] == 1:
                self.info('turn robot and camera on')
                try:
                    if self._startupRobotAndCam():
                        power = True
                except TypeError, e:
                    self.error(str(e))
            else:
                self.error('unknown robot and camera message received from GSN')
                
            heater = None
            if data[2] == 0:
                self.info('turn heater off')
                self.getPowerControlObject().ext3Off()
                heater = False
            elif data[2] == 1:
                self.info('turn heater on')
                self.getPowerControlObject().ext3On()
                heater = True
            else:
                self.error('unknown heater message received from GSN')
                
            str = ''
            if heater == True:
                if power == True:
                    str = 'CamZilla robot has been turned on and '
                elif power == False:
                    str = 'CamZilla robot has been turned off and '
                str += 'heater is turned on'
            else:
                if power == True:
                    str = 'CamZilla robot has been turned on and '
                elif power == False:
                    str = 'CamZilla robot has been turned off and '
                str += 'heater is turned off'
                
            self.processMsg(self.getTimeStamp(), [int(now*1000)] + ['power', str, self._x, self._y] + [None]*8)
        else:
            self.error('unknown message type received from GSN')
        
        
    def _parseTask(self, task):
        params = task.strip().split(' ')
        ret = [None]*8
        for param in params:
            param = param.lower()
            if param.startswith('start'):
                startX, startY = param[6:-1].split(',')
                ret[0] = float(startX)
                ret[1] = float(startY)
            elif param.startswith('pictures'):
                picsX, picsY = param[9:-1].split(',')
                ret[2] = int(picsX)
                ret[3] = int(picsY)
            elif param.startswith('rotation'):
                rotationX, rotationY = param[9:-1].split(',')
                ret[4] = float(rotationX)
                ret[5] = float(rotationY)
            elif param.startswith('delay'):
                ret[6] = int(param[6:-1])
            elif param.startswith('gphoto2'):
                ret[7] = param[8:-1].split(',')
            else:
                self.error('unrecognized parameter >%s< in task >%s<' % (param,task))
        if ret[0] is None:
            ret[0] = 0.0
        if ret[1] is None:
            ret[1] = 0.0
        if ret[2] is None:
            ret[2] = 1
        if ret[3] is None:
            ret[3] = 1
        if ret[4] is None and ret[2] > 1:
            raise TypeError('x-rotation has to be specified if more than one picture has to be taken in x-direction')
        if ret[5] is None and ret[3] > 1:
            raise TypeError('y-rotation has to be specified if more than one picture has to be taken in y-direction')
        if ret[4] is None:
            ret[4] = 1.0
        if ret[5] is None:
            ret[5] = 1.0
        if ret[6] is None:
            ret[6] = 0
        if ret[7] is None:
            ret[7] = []
        return ret
        
        
        
    def _takePicture(self, settings):
        configlist = []
        
        for default in DEFAULT_GPHOTO2_SETTINGS:
            notavailable = True
            def_begin = default.split('=')[0].strip()
            for setting in settings:
                if def_begin == setting.split('=')[0].strip():
                    notavailable = False
                    break
            if notavailable:
                settings.append(default)
        
        sets = []
        ret = ''
        for setting in settings:
            ret += setting + ', '
            sets.append('--set-config %s' % (setting.strip(),))
        if ret:
            ret = ret[:-2]
        
        command = [GPHOTO2, '--port="usb:"', '--force-overwrite', '--quiet'] + sets + ['--capture-image']
        com = ''
        for entry in command:
            com += entry + ' '
        self.debug('taking picture >%s<' % (com,))
        self._execGphoto2(command)
        return ret.strip()
        
        
    def _downloadPictures(self, datestring):
        self.info('downloading all pictures from photo camera')
        self._execGphoto2([GPHOTO2, '--port="usb:"', '--quiet', '--get-all-files', '--filename=' + datestring + '-%03n.%C', '--recurse', '--delete-all-files'], PICTUREFOLDER)
        
        
    def _execGphoto2(self, params, cwd=None):
        p = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        ret = p.wait()
        output = p.communicate()
        if output[0]:
            self.info(output[0])
        if ret == 0:
            if output[1]:
                self.warning(output[1])
        else:
            if self._power:
                if output[1]:
                    self.error(output[1])
            else:
                raise Exception('camera has no more power -> gphoto2 could not execute command')
    
    
    def _shutdownRobotAndCam(self):
        if self._power:
            if self._serial.isOpen():
                self._serial.close()
            self._power = False
            # turn the USB2 port off
            self.getPowerControlObject().usb2Off()
            # turn the USB3 port off
            self.getPowerControlObject().usb3Off()
            # turn the robot and photo camera off
            self.getPowerControlObject().ext1Off()
            return True
        return False
        
    
    def _startupRobotAndCam(self):
        if not self._power:
            self.info('wait for robot to startup')
            # turn the USB2 port on
            self.getPowerControlObject().usb2On()
            # turn the USB3 port on
            self.getPowerControlObject().usb3On()
            # turn the robot and photo camera on
            self.getPowerControlObject().ext1On()
            self._power = True
            
            if not self._serial or not self._serial.isOpen():
                cnt = 0
                while not self._plugStop:
                    try:
                        self._serial.open()
                    except serial.SerialException, e:
                        if cnt == 5:
                            raise TypeError('could not initialize serial source: %s' % (e,))
                    else:
                        self.info(self._serial.readline())
                        break
                    self._delay.wait(0.5)
                    cnt += 1
                    
            self.info('robot ready')
            return True
        return False
        
        
    def _calibrateRobot(self):
        if self._power:
            self._write("j=off")
            cal = self._write("cal")
            self._xRotationToPulse = cal[0] / (self._xMaxRotation / 2.0)
            self._yRotationToPulse = cal[1] / (self._yMaxRotation / 2.0)
        else:
            self.error('robot not powered -> can not calibrate')
            
            
    def _position(self, x=None, y=None):
        if x is not None:
            self._write('x=%d' % (int(round(x*self._xRotationToPulse)),))
            self._x = x
        if y is not None:
            self._write('y=%d' % (int(round(y*self._yRotationToPulse)),))
            self._y = y
        
        
        
    def _write(self, com):
        if not self._plugStop:
            try:
                self._writeLock.acquire()
                self.debug('servo control write: %s' % (com,))
                if com == 'j=on' or com == 'j=off':
                    self._serial.write(com + "\n")
                    ans = self._serial.readline().strip()
                    self.debug('servo control answer: j=..: %s' % (ans,))
                    if com != ans:
                        raise Exception('return value (%s) does not match command (%s)' % (ans, com))
                    self._manualControl = (com == 'j=on')
                elif self._manualControl:
                    raise Exception('manual joystick control is turned on -> command (%s) will not be executed' % (com,))
                elif com == 'cal':
                    self._serial.write(com + "\n")
                    cal1 = self._serial.readline().strip()
                    if cal1 == 'j=on':
                        self._manualControl = True
                        raise Exception('manual joystick control has been turned on -> no more commands will be sent to CamZilla until joystick control has been turned off')
                    elif cal1 == '!cal':
                        raise Exception('could not calibrate')
                    self.debug('servo control answer: cal(1): %s' % (cal1))
                    cal2 = self._serial.readline().strip()
                    self.debug('servo control answer: cal(2): %s' % (cal2))
                    cal1 = cal1[5:-1].split(',')
                    cal2 = cal2.split('=')[1].split('/')
                    return (int(cal1[0]), int(cal1[1]), int(cal2[0]), int(cal2[1]))
                elif com.startswith('x=') or com.startswith('y='):
                    self._serial.write(com + "\n")
                    ans = self._serial.readline().strip()
                    self.debug('servo control answer: x=..: %s' % (ans,))
                    if ans == '!cal':
                        raise Exception('not yet calibrated')
                    elif ans.startswith('x/y='):
                        spl = ans.split('=')[1].split('/')
                        xLimit = yLimit = False
                        if (spl[0].endswith('L')):
                            spl[0] = spl[0][:-1]
                            xLimit = True
                        if (spl[1].endswith('L')):
                            spl[1] = spl[1][:-1]
                            yLimit = True
                        return (int(spl[0]), int(spl[1]), xLimit, yLimit)
                    elif ans == 'j=on':
                        self._manualControl = True
                        raise Exception('manual joystick control has been turned on -> no more commands will be sent to CamZilla until joystick control has been turned off')
                    else:
                        raise Exception('unknown return value for command (%s): %s' % (com, ans))
                else:
                    raise TypeError('command (%s) unknown' % (com,))
            except Exception, e:
                raise e
            finally:
                self._writeLock.release()
        else:
            self.warning('plugin has been stopped -> command will not be executed')
            
    


if __name__ == '__main__':
    import signal
    import ConfigParser
    import optparse
    import logging.config

    class GSNPeerDummy():
        def processMsg(self, msgType, timestamp, payload, priority, backlog=False):
            pass
    class MainDummy():
        def __init__(self):
            self.gsnpeer = GSNPeerDummy()
            self.duty_cycle_mode = False
        def incrementExceptionCounter(self):
            pass
        def incrementErrorCounter(self):
            pass
        def runPluginRemoteAction(self):
            pass
    
    parser = optparse.OptionParser('usage: %prog [options]')
    
    parser.add_option('-c', '--config', type='string', dest='config_file', default='/etc/backlog.cfg',
                      help='Configuration file. Default: /etc/backlog.cfg', metavar='FILE')
    parser.add_option('-x', '--startx', type='int', dest='startX', default=0,
                      help='Lower-left horizontal starting point', metavar='INT')
    parser.add_option('-y', '--starty', type='int', dest='startY', default=0,
                      help='Lower-left vertical starting point', metavar='INT')
    parser.add_option('--picsx', type='int', dest='picturesX', default=1,
                      help='Number of pictures taken horizontally', metavar='INT')
    parser.add_option('--picsy', type='int', dest='picturesY', default=1,
                      help='Number of pictures taken vertically', metavar='INT')
    parser.add_option('--rotx', type='int', dest='rotationX', default=1,
                      help='Horizontal rotation in degrees between pictures', metavar='INT')
    parser.add_option('--roty', type='int', dest='rotationY', default=1,
                      help='Vertical rotation in degrees between pictures', metavar='INT')
    parser.add_option('-d', '--delay', type='int', dest='delay', default=0,
                      help='Delay between rotation and picture taking', metavar='INT')
    parser.add_option('-g', '--gphoto2', type='string', dest='gphoto2', default='/main/settings/capturetarget=1,/main/imgsettings/imagequality=0,/main/imgsettings/imagesize=2',
                      help='Comma separated configurations for gphoto2', metavar='CONFIGS')
    
    (opt, args) = parser.parse_args()

    # read config file for logging options
    try:
        logging.config.fileConfig(opt.config_file)
        logging.logProcesses = 0

        # read config file for other options
        config = ConfigParser.SafeConfigParser()
        config.optionxform = str # case sensitive
        config.read(opt.config_file)
    except ConfigParser.NoSectionError, e:
        print e.__str__()
    
    try:
        camZilla = CamZillaPluginClass(MainDummy(), dict(config.items('CamZillaPlugin_options')))
        camZilla.start()
        camZilla.action('start(%d,%d) pictures(%d,%d) rotation(%d,%d) delay(%d) gphoto2(%s)' % (opt.startX, opt.startY, opt.picturesX, opt.picturesY, opt.rotationX, opt.rotationY, opt.delay, opt.gphoto2))
        signal.pause()
    except KeyboardInterrupt:
        print 'KeyboardInterrupt'
        camZilla.stop()
        