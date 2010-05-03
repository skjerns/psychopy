"""Basic functions, including timing and run-time configuration profile
"""
# Part of the PsychoPy library
# Copyright (C) 2010 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

import sys, platform, os, time, threading
import subprocess, shlex, numpy

# these are for RuntimeInfo():
from psychopy import __version__ as psychopyVersion
from pyglet.gl import gl_info
import scipy, matplotlib, pyglet
try: import ctypes
except: pass
try: import hashlib # python 2.5
except: import sha

# no longer try: except: here -- want exceptions to trip us up (because things are coded defensively in rush)
from psychopy.ext import rush

runningThreads=[]
try:
    import pyglet.media
except:
    pass
    
def quit():
    """Close everything and exit nicely (ending the experiment)
    """
    #pygame.quit() #safe even if pygame was never initialised
    for thisThread in threading.enumerate():
        if hasattr(thisThread,'stop') and hasattr(thisThread,'running'):
            #this is one of our event threads - kill it and wait for success
            thisThread.stop()
            while thisThread.running==0:
                pass#wait until it has properly finished polling
    sys.exit(0)#quits the python session entirely

#set the default timing mechanism
"""(The difference in default timer function is because on Windows,
clock() has microsecond granularity but time()'s granularity is 1/60th
of a second; on Unix, clock() has 1/100th of a second granularity and
time() is much more precise.  On Unix, clock() measures CPU time 
rather than wall time.)"""
if sys.platform == 'win32':
    getTime = time.clock
else:
    getTime = time.time

class Clock:
    """A convenient class to keep track of time in your experiments.
    You can have as many independent clocks as you like (e.g. one 
    to time	responses, one to keep track of stimuli...)
    The clock is based on python.time.time() which is a sub-millisec
    timer on most machines. i.e. the times reported will be more
    accurate than you need!
    """
    def __init__(self):
        self.timeAtLastReset=getTime()#this is sub-millisec timer in python
    def getTime(self):
        """Returns the current time on this clock in secs (sub-ms precision)
        """
        return getTime()-self.timeAtLastReset
    def reset(self, newT=0.0):
        """Reset the time on the clock. With no args time will be 
        set to zero. If a float is received this will be the new
        time on the clock
        """
        self.timeAtLastReset=getTime()+newT

def wait(secs, hogCPUperiod=0.2):
    """Wait for a given time period. 
    
    If secs=10 and hogCPU=0.2 then for 9.8s python's time.sleep function will be used,
    which is not especially precise, but allows the cpu to perform housekeeping. In
    the final hogCPUperiod the more precise method of constantly polling the clock 
    is used for greater precision.
    """
    #initial relaxed period, using sleep (better for system resources etc)
    if secs>hogCPUperiod:
        time.sleep(secs-hogCPUperiod)
        secs=hogCPUperiod#only this much is now left
        
    #hog the cpu, checking time
    t0=getTime()
    while (getTime()-t0)<secs:
        pass
    
    #we're done, let's see if pyglet collected any event in meantime
    try:
        pyglet.media.dispatch_events()
    except:
        pass #maybe pyglet 


def shellCall(shellCmd, stderr=False):
    """Calls a system command via subprocess, returns the stdout from the command.
    
    returns (stdout,stderr) if kwarg stderr==True
    """
    
    shellCmdList = shlex.split(shellCmd) # safely split into command + list-of-args; pipes don't work here
    stdoutData, stderrData = subprocess.Popen(shellCmdList,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE ).communicate()
        
    if stderr:
        return stdoutData.strip(), stderrData.strip()
    else:
        return stdoutData.strip()

def svnVersion(file):
    """Tries to discover the svn version (revision #) for a file.
    
    Not thoroughly tested; completely untested on Windows Vista, Win 7, FreeBSD
    """
    if not (os.path.exists(file) and os.path.isdir(os.path.join(os.path.dirname(file),'.svn'))):
        return None, None, None
    svnRev, svnLastChangedRev, svnUrl = None, None, None
    if sys.platform in ['darwin', 'linux2', 'freebsd']:
        svninfo,stderr = shellCall('svn info "'+file+'"', stderr=True) # expects a filename, not dir
        for line in svninfo.splitlines():
            if line.find('URL:') == 0:
                svnUrl = line.split()[1]
            elif line.find('Revision: ') == 0:
                svnRev = line.split()[1]
            elif line.find('Last Changed Rev') == 0:
                svnLastChangedRev = line.split()[3]
    else: # worked for me on Win XP sp2 with TortoiseSVN (SubWCRev.exe)
        stdout,stderr = shellCall('subwcrev "'+file+'"', stderr=True)
        for line in stdout.splitlines():
            if line.find('Last committed at revision') == 0:
                svnRev = line.split()[4]
            elif line.find('Updated to revision') == 0:
                svnLastChangedRev = line.split()[3]
    return svnRev, svnLastChangedRev, svnUrl

def hgVersion(file):
    """Tries to discover the mercurial (hg) changeset for a file's directory.
    
    Not thoroughly tested; completely untested on Windows Vista, Win 7, FreeBSD
    """
    if not (os.path.exists(file) and os.path.isdir(os.path.join(os.path.dirname(file),'.hg'))):
        return None
    hgRev = None
    if sys.platform in ['darwin', 'linux2', 'freebsd']:
        hginfo,stderr = shellCall('hg log "'+file+'"', stderr=True)
        try:
            hglines = hginfo.splitlines()
            hgRev = hglines[0].split()[-1]
            if hglines[1].find('tag:')==0:
                hgRev += ' [%s]' % ''.join(hglines[1].split())
        except:
            pass
    else:
        pass # placeholder for win32
    return hgRev

def getUserNameUID():
    """return user name, UID: -1=undefined, 0=assume full root, >499=assume non-root; but its >999 on debian
    """
    try:
        user = os.environ['USER']
    except:
        user = os.environ['USERNAME']
    uid = '-1' 
    try:
        if sys.platform not in ['win32']:
            uid = os.popen('id -u').read()
        else:
            try:
                uid = '1000'
                if ctypes.windll.shell32.IsUserAnAdmin():
                    uid = '0'
            except:
                raise
    except:
        pass
    return str(user), int(uid)

def sha1Digest(str):
    """returns base64 / hex encoded sha1 digest of a file or string, using hashlib.sha1() if available
    """
    try:
        sha1 = hashlib.sha1()
    except:
        sha1 = sha.new() # deprecated, here for python 2.4
    if os.path.isfile(str):
        f = open(str,'r')
        sha1.update(f.read())
        f.close()
    else:
        sha1.update(str)
    return sha1.hexdigest()
    
def msPerFrame(myWin, nFrames=60, showVisual=True, msg='', msDelay=0.):
    """Assesses the monitor refresh rate (average, median, SD) under current conditions.
    
    Records time for each refresh (frame) for n frames (at least 60), while displaying an optional visual.
    The visual is just eye-candy to show that something is happening when assessing many frames. You can
    also give it text to display instead of a visual,
    e.g., msg='(testing refresh rate...)'; setting msg implies showVisual == False.
    To simulate refresh rate under cpu load, you can specify a time to wait within the loop prior to
    doing the win.flip(). If 0 < msDelay < 100, wait for that long in ms.
    
    Returns timing stats (in ms) of:
    - average time per frame, for all frames
    - standard deviation of all frames
    - median, as the average of 12 frame times around the median (~monitor refresh rate)
    """
    
    from psychopy import visual # which imports core, so currently need to do here in core.msPerFrame()
    
    nFrames = max(60, nFrames)  # lower bound of 60 samples--need enough to estimate the SD
    num2avg = 12  # how many to average from around the median
    if len(msg):
        showVisual = False
        showText = True
        myMsg = visual.TextStim(myWin, text=msg, italic=True, 
                            color=(.7,.6,.5),colorSpace='rgb', height=0.1)
    else:
        showText = False
    if showVisual:
        x,y = myWin.size
        myStim = visual.PatchStim(myWin, tex='sin', mask='gauss', size=(float(y)/x,1.0), sf=3.0, opacity=.2)
    clockt = [] # clock times
    drawt  = [] # end of drawing time, in clock time units, for testing how long myStim.draw() takes
    
    if msDelay > 0 and msDelay < 100:
        doWait = True
        delayTime = msDelay/1000. #sec
    else:
        doWait = False
        
    winUnitsSaved = myWin.units 
    myWin.units = 'norm' # norm is required for the visual (or text) display
    
    # accumulate secs per frame (and time-to-draw) for a bunch of frames:
    rush(True)
    for i in range(5): # wake everybody up
        myWin.flip()
    for i in range(nFrames): # ... and go for real this time
        clockt.append(getTime()) 
        if showVisual:
            myStim.setPhase(1.0/nFrames, '+')
            myStim.setSF(3./nFrames, '+')
            myStim.setOri(12./nFrames,'+')
            myStim.setOpacity(.9/nFrames, '+')
            myStim.draw()
        elif showText:
            myMsg.draw()
        if doWait:
            wait(delayTime)
        drawt.append(getTime())
        myWin.flip()
    rush(False)
    
    myWin.units = winUnitsSaved # restore
    
    frameTimes = [(clockt[i] - clockt[i-1]) for i in range(1,len(clockt))]
    drawTimes  = [(drawt[i] - clockt[i]) for i in range(len(clockt))] # == drawing only
    freeTimes = [frameTimes[i] - drawTimes[i] for i in range(len(frameTimes))] # == unused time
    
    # cast to float so that the resulting type == type(0.123)
    frameTimes.sort() # for median
    msPFmed = 1000. * float(numpy.average(frameTimes[ (nFrames-num2avg)/2 : (nFrames+num2avg)/2 ])) # median-most slice
    msPFavg = 1000. * float(numpy.average(frameTimes)) 
    msPFstd = 1000. * float(numpy.std(frameTimes))
    msdrawAvg = 1000. * float(numpy.average(drawTimes))
    msdrawSD = 1000. * float(numpy.std(drawTimes))
    msfree = 1000. * float(numpy.average(freeTimes))
    #print "draw=%.1fms free=%.1fms pad=%.1fms" % (msdrawAvg,msfree,msDelay)
    
    return msPFavg, msPFstd, msPFmed #, msdrawAvg, msdrawSD, msfree
    

class RuntimeInfo(dict):
    """Returns a snapshot of your configuration at run-time, for immediate or archival use.
    
    Returns a dict-like object with info about PsychoPy, your experiment script, the system & OS,
    your window and monitor settings (if any), python & packages, and openGL.
    
    Example usage: see runtimeInfo.py in coder demos
    """
    def __init__(self, author=None, version=None, win=None, refreshTest=None,
                 userProcsDetailed=False, verbose=False, randomSeed=None ):
        """
        :Parameters:
            
            win : *None*, psychopy.visual.Window() instance
                what window to use for refresh rate testing (if any) and settings (if win != None)
            author : *None*, string
                string for user-supplied author info (of an experiment, sys.argv[0])
            version : *None*, string
                string for user-supplied version info (of an experiment, sys.argv[0])
            verbose : *False*, True
                True put
            refreshTest : *None*, False, True, 'progressBar'
                if refreshTest, then assess refresh average, median, and SD of 60 win.flip()s, using core.msPerFrame()
            userProcsDetailed: *False*, True
                get details about concurrent user's processses (command, process-ID)
            randomSeed: *None*
                a way for the user to record what their random seed was; it is not set, merely recorded
                None defaults to time.ctime() as the seed (== self['experimentRunDateTime'])
                
        :Returns a flat dict: in categories
            
            psychopy : version
                psychopyVersion
            experiment : author, version, directory, name, current time-stamp, SHA1 digest, svn or hg info (if any)
                experimentAuthor, experimentVersion, ...
            system : hostname, platform, user login, count of users, user process info (count, cmd + pid), flagged processes
                systemHostname, systemPlatform, ...
            window : (see output; many details about the refresh rate, window, and monitor; units are noted)
                windowWinType, windowWaitBlanking, ...windowRefreshTimeSD_ms, ... windowMonitor.<details>, ...
            python : version of python, versions of key packages (numpy, scipy, matplotlib, pyglet, pygame)
                pythonVersion, pythonScipyVersion, ...
            openGL : version, vendor, rendering engine, plus info on whether key extensions are present
                openGLVersion, ..., openGLextGL_EXT_framebuffer_object, ...
        """
        from psychopy import visual # have to do this in __init__ (visual imports core)
        
        dict.__init__(self)  # this will cause an object to be created with all the same methods as a dict
        
        self['psychopyVersion'] = psychopyVersion
        self['psychopyHaveExtRush'] = rush(False) # NB: this looks weird, but avoids setting high-priority incidentally
        
        self._setExperimentInfo(author,version,verbose,randomSeed)
        self._setSystemUserInfo()
        self._setCurrentProcessInfo(verbose, userProcsDetailed)
        
        # need a window for frame-timing, and some openGL drivers want a window open
        # rewrite so that its not always necessary to open a window if you just want system info (but not monitor / window)
        if win == None: # make a temporary window, later close it
            win = visual.Window(fullscr=True, monitor="testMonitor", allowGUI=False, units='norm')
            refreshTest = 'progressBar'
            usingTempWin = True
        else: # we were passed a window instance, use it for timing and profile it:
            usingTempWin = False
        self._setWindowInfo(win, verbose, refreshTest, usingTempWin)
       
        self['pythonVersion'] = sys.version.split()[0] # always do this, not just if verbose
        if verbose:
            self._setPythonInfo()
            self._setOpenGLInfo()
        if usingTempWin:
            win.close() # close after doing openGL
            
    def _setExperimentInfo(self,author,version,verbose,randomSeed):
        self['experimentRuntimeEpoch'] = time.time() # plausible basis for random.seed()
        self['experimentRuntime'] = time.ctime(self['experimentRuntimeEpoch'])+' '+time.tzname[time.daylight] # a "right now" time-stamp
        if author or verbose:  
            self['experimentAuthor'] = author
        if version or verbose: 
            self['experimentAuthVersion'] = version
        
        # script identity & integrity information:
        # sha1 digest
        self['experimentScriptDigestSHA1'] = sha1Digest(os.path.abspath(sys.argv[0]))
        # subversion revision?
        self['experimentScript'] = os.path.basename(sys.argv[0])  # file name
        scriptDir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self['experimentScriptDirectory'] = scriptDir
        svnrev, last, url = svnVersion(os.path.abspath(sys.argv[0])) # svn revision
        if svnrev or verbose:
            self['experimentScriptSvnRevision'] = svnrev
            if verbose: self['experimentScriptSvnRevLast'] = last
            self['experimentScriptSvnRevURL'] = url
        # mercurical revision?
        hgcs = hgVersion(os.path.abspath(sys.argv[0])) 
        if hgcs or verbose:
            self['experimentScriptHgChangeSet'] = hgcs
        
        # random.seed -- here, just record the value to be set later; later do: random.seed(info['randomSeed'])
        if randomSeed or verbose:
            if randomSeed == 'time':
                randomSeed = self['experimentRuntimeEpoch']
            self['experimentRandomSeed'] = randomSeed
        
    def _setSystemUserInfo(self):
        # machine name
        self['systemHostName'] = platform.node()
        
        # platform name, etc
        if sys.platform in ['darwin']:
            OSXver, junk, architecture = platform.mac_ver()
            platInfo = 'darwin '+OSXver+' '+architecture
            # powerSource = ...
        elif sys.platform in ['linux2']:
            platInfo = 'linux2 '+platform.release()
            # powerSource = ...
        elif sys.platform in ['win32']:
            platInfo = 'win32 windowsversion='+repr(sys.getwindowsversion())
            # powerSource = ...
        else:
            platInfo = ' [?]'
            # powerSource = ...
        self['systemPlatform'] = platInfo
        #self['systemPowerSource'] = powerSource
        
        # count all unique people (user IDs logged in), and find current user name & UID
        self['systemUser'],self['systemUserID'] = getUserNameUID()
        try:
            users = shellCall("who -q").splitlines()[0].split()
            self['systemUsersCount'] = len(set(users))
        except:
            self['systemUsersCount'] = False
        
        # when last rebooted?
        try:
            lastboot = shellCall("who -b").split()
            self['systemRebooted'] = ' '.join(lastboot[2:])
        except:
            self['systemRebooted'] = "[?]"
        
        # crypto tools; redundant with python distribution info?
        try:
            self['systemOpenSSLVersion'],err = shellCall('openssl version',stderr=True)
            if err:
                raise
        except:
            self['systemOpenSSLVersion'] = None
        
    def _setCurrentProcessInfo(self, verbose=False, userProcsDetailed=False):
        # what other processes are currently active for this user?
        profileInfo = ''
        appFlagList = [# flag these apps if active, case-insensitive match:
            'Firefox','Safari','Explorer','Netscape', 'Opera', # web browsers can burn CPU cycles
            'BitTorrent', 'iTunes', # but also matches iTunesHelper (add to ignore-list)
            'mdimport', # can have high CPU
            'Office', 'KeyNote', 'Pages', 'LaunchCFMApp', # productivity; on mac, MS Office (Word etc) can be launched by 'LaunchCFMApp'
            'VirtualBox','VBoxClient', # virtual machine as host or client
            'Parallels', 'Coherence', 'prl_client_app','prl_tools_service',
            'VMware'] # just a guess
        appIgnoreList = [# always ignore these, exact match:
            'ps','login','-tcsh','bash', 'iTunesHelper']
        
        # assess concurrently active processes owner by the current user:
        try:
            # ps = process status, -c to avoid full path (potentially having spaces) & args, -U for user
            if sys.platform in ['darwin']:
                proc = shellCall("ps -c -U "+os.environ['USER'])
                cmdStr = 'COMMAND'
            elif sys.platform in ['linux2']:
                proc = shellCall("ps -c -U "+os.environ['USER'])
                cmdStr = 'CMD'
            elif sys.platform in ['win32']: 
                proc, err = shellCall("tasklist", stderr=True) # "tasklist /m" gives modules as well
                if err:
                    print 'tasklist error:', err
                    raise
            else: # guess about freebsd based on darwin... 
                proc,err = shellCall("ps -U "+os.environ['USER'],stderr=True)
                if err: raise
                cmdStr = 'COMMAND' # or 'CMD'?
            systemProcPsu = []
            systemProcPsuFlagged = [] 
            systemUserProcFlaggedPID = []
            procLines = proc.splitlines() 
            headerLine = procLines.pop(0) # column labels
            if sys.platform not in ['win32']:
                cmd = headerLine.split().index(cmdStr) # columns and column labels can vary across platforms
                pid = headerLine.split().index('PID')  # process id's extracted in case you want to os.kill() them from psychopy
            else: # this works for win XP, for output from 'tasklist'
                procLines.pop(0) # blank
                procLines.pop(0) # =====
                pid = -5 # pid next after command, which can have
                cmd = 0  # command is first, but can have white space, so end up taking line[0:pid]
            for p in procLines:
                pr = p.split() # info fields for this process
                if pr[cmd] not in appIgnoreList:
                    if sys.platform in ['win32']:  #allow for spaces in app names, replace with '_'
                        systemProcPsu.append(['_'.join(pr[cmd:pid]),pr[pid]]) # later just count these unless want details
                    else:
                        systemProcPsu.append(['_'.join(pr[cmd:]),pr[pid]]) #
                    for app in appFlagList:
                        if p.lower().find(app.lower())>-1: # match anywhere in the process line
                            systemProcPsuFlagged.append([app, pr[pid]])
                            systemUserProcFlaggedPID.append(pr[pid])
            self['systemUserProcCount'] = len(systemProcPsu)
            self['systemUserProcFlagged'] = systemProcPsuFlagged
            
            if verbose and userProcsDetailed:
                self['systemUserProcCmdPid'] = systemProcPsu
                self['systemUserProcFlaggedPID'] = systemUserProcFlaggedPID
            
            """
            # its possible to suspend flagged applications while running your exp, which is a little dangerous
            # you can lose data if you forget to unsuspend, or if you suspend something critical
            suspendNonessentialApps = False # edit this to enable
            self.suspendedApps = []
            if verbose and userProcsDetailed and suspendNonessentialApps and sys.platform in ['darwin']:
                for PID in self['systemUserProcPsuFlaggedPID']:
                    os.popen("kill -STOP "+PID) # temporarily suspend flagged applications
                    self.suspendedApps.append(PID)
            # and you have to to do this (-CONT) after the key part of your experiment:
            # i.e., you have to loop over suspendApps and unsuspend each one
            for PID in self.suspendedApps: # comment out this code here, otherwise you'll immediately unsuspend things
                os.popen("kill -CONT "+PID) 
            """
        except:
            if verbose:
                self['systemUserProcCmdPid'] = None
                self['systemUserProcFlagged'] = None
    
    def _setWindowInfo(self, win=None, verbose=False, refreshTest='grating', usingTempWin=True):
        """find and store info about the window: refresh rate, configuration info
        """
        
        if refreshTest in ['grating', True]:
            msPFavg, msPFstd, msPFmd6 = msPerFrame(win, nFrames=120, showVisual=bool(refreshTest=='grating'))
            self['windowRefreshTimeAvg_ms'] = msPFavg
            self['windowRefreshTimeMedian_ms'] = msPFmd6
            self['windowRefreshTimeSD_ms'] = msPFstd
            # could be useful to do twice: under the best possible conditions msPerFrame(win, nFrames=120, msDelay=0, showVisual=False)
            # and when there's only 0.5ms free time: msPerFrame(win, nFrames=120, msDelay=msPFmd6-0.5, showVisual=False)
            #self['windowRefreshTimeDelayAvg_ms'] = msPFavg
            #self['windowRefreshTimeDelayMedian_ms'] = msPFmd6
            #self['windowRefreshTimeDelaySD_ms'] = msPFstd
        if usingTempWin:
            return
        
        # These 'configuration lists' control what attributes are reported.
        # All desired attributes/properties need a legal internal name, e.g., win.winType.
        # If an attr is callable, its gets called with no arguments, e.g., win.monitor.getWidth()
        winAttrList = ['winType', '_isFullScr', 'units', 'monitor', 'pos', 'screen', 'rgb', 'size']
        winAttrListVerbose = ['allowGUI', 'useNativeGamma', 'recordFrameIntervals','waitBlanking', '_haveShaders', '_refreshThreshold']
        if verbose: winAttrList += winAttrListVerbose
        
        monAttrList = ['name', 'getDistance', 'getWidth', 'currentCalibName']
        monAttrListVerbose = ['_gammaInterpolator', '_gammaInterpolator2']
        if verbose: monAttrList += monAttrListVerbose
        if 'monitor' in winAttrList: # replace 'monitor' with all desired monitor.<attribute>
            i = winAttrList.index('monitor') # retain list-position info, put monitor stuff there
            del(winAttrList[i])
            for monAttr in monAttrList:
                winAttrList.insert(i, 'monitor.' + monAttr)
                i += 1
        for winAttr in winAttrList: 
            try:
                attrValue = eval('win.'+winAttr)
            except AttributeError:
                log.warning('AttributeError in RuntimeInfo._setWindowInfo(): Window instance has no attribute', winAttr)
                continue
            if hasattr(attrValue, '__call__'):
                try:
                    a = attrValue()
                    attrValue = a
                except:
                    print 'Warning: could not get a value from win.'+winAttr+'()  (expects arguments?)'
                    continue
            while winAttr[0]=='_':
                winAttr = winAttr[1:]
            winAttr = winAttr[0].capitalize()+winAttr[1:]
            winAttr = winAttr.replace('Monitor._','Monitor.')
            if winAttr in ['Pos','Size']:
                winAttr += '_pix'
            if winAttr in ['Monitor.getWidth','Monitor.getDistance']:
                winAttr += '_cm'
            if winAttr in ['RefreshThreshold']:
                winAttr += '_sec'
            self['window'+winAttr] = attrValue
        
    def _setPythonInfo(self):
        # External python packages:
        self['pythonNumpyVersion'] = numpy.__version__
        self['pythonScipyVersion'] = scipy.__version__
        self['pythonMatplotlibVersion'] = matplotlib.__version__
        self['pythonPygletVersion'] = pyglet.__version__
        try: from pygame import __version__ as pygameVersion
        except: pygameVersion = '(no pygame)'
        self['pythonPygameVersion'] = pygameVersion
            
        # Python gory details:
        self['pythonFullVersion'] = sys.version.replace('\n',' ')
        self['pythonExecutable'] = sys.executable
        
    def _setOpenGLInfo(self):
        # OpenGL info:
        self['openGLVendor'] = gl_info.get_vendor()
        self['openGLRenderingEngine'] = gl_info.get_renderer()
        self['openGLVersion'] = gl_info.get_version()
        GLextensionsOfInterest=['GL_ARB_multitexture', 'GL_EXT_framebuffer_object','GL_ARB_fragment_program',
            'GL_ARB_shader_objects','GL_ARB_vertex_shader', 'GL_ARB_texture_non_power_of_two','GL_ARB_texture_float']
    
        for ext in GLextensionsOfInterest:
            self['openGLext'+ext] = bool(gl_info.have_extension(ext))
        
    def __repr__(self):
        """ Return a string that is a legal python (dict), and close to YAML and configObj syntax
        """
        info = '{\n#[ PsychoPy2 RuntimeInfoStart ]\n'
        sections = ['PsychoPy', 'Experiment', 'System', 'Window', 'Python', 'OpenGL']
        for sect in sections:
            info += '  #[[ %s ]] #---------\n' % (sect)
            sectKeys = [k for k in self.keys() if k.lower().find(sect.lower()) == 0]
            # get keys for items matching this section label; use reverse-alpha order if easier to read:
            sectKeys.sort(key=str.lower, reverse=bool(sect in ['PsychoPy', 'Window', 'Python', 'OpenGL']))
            for k in sectKeys:
                selfk = self[k] # alter a copy for display purposes
                try:
                    if type(selfk) == type('abc'):
                        selfk = selfk.replace('"','').replace('\n',' ')
                    elif k.find('_ms')> -1: #type(selfk) == type(0.123):
                        selfk = "%.3f" % selfk
                    elif k.find('_sec')> -1:
                        selfk = "%.4f" % selfk
                    elif k.find('_cm')>-1:
                        selfk = "%.1f" % selfk
                except:
                    pass
                if k in ['systemUserProcFlagged','systemUserProcCmdPid'] and len(selfk): # then strcat unique proc names
                    prSet = []
                    for pr in self[k]: # str -> list of lists
                        prSet += [pr[0]] # first item in sublist is proc name (CMD)
                    selfk = ' '.join(list(set(prSet)))
                info += '    "%s": "%s",\n' % (k, selfk)
        info += '#[ PsychoPy2 RuntimeInfoEnd ]\n}\n'
        return info
    
    def __str__(self):
        """ Return a string intended for printing to a log file
        """
        infoLines = self.__repr__()
        info = infoLines.splitlines()[1:-1] # remove enclosing braces from repr
        for i,line in enumerate(info):
            if line.find('openGLext')>-1: # swap order for OpenGL extensions -- much easier to read
                tmp = line.split(':')
                info[i] = ': '.join(['   '+tmp[1].replace(',',''),tmp[0].replace('    ','')+','])
        info = '\n'.join(info).replace('",','').replace('"','')+'\n'
        return info
    
    def _type(self):
        # for debugging
        sk = self.keys()
        sk.sort()
        for k in sk:
            print k,type(self[k]),self[k]
            