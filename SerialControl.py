from __future__ import division

import pandas as pd
import datetime
import time
import os
import sys
import serial

import msvcrt as m
import numpy as np
from numpy.random import shuffle
import random

import colorama as color # makes things look nice
from colorama import Fore as fc
from colorama import Back as bc     
from colorama import Style

from utilities.args import args
from utilities.numerical import num, na_printr, unpack_table

"""
1. The program starts
2. The program opens communications with available serial ports
3. The program starts a block
4. The program shuffles the stimuli (frequecies list)
5. The program transmits the frequenices to the stimbox
    -The stimbox cues the stimuli in memory
6. The program initiates a trial by sending a mode flag to
   the behaviour box.
   - The behaviour box runs one trial at a time; waiting
      for a flag from Serial each time
   - This means that inter-trial intervals must be controlled
     by the Serial controller. (this program)
   - This means this program must know when there is a timeout
     or not
7. The program records the output from behaviorCOMs into a
   behaviourdf.
8. The program repeats sending mode flags until all stimuli have
   been presented.
9. The program calculates d_prime|any_stimuls; d`|rising; d`|falling

--------------------------------------------------------------------
Arguments
--------------------------------------------------------------------
"""


verbose = args.verbose # this will be a cmdline parameter
port = args.port # a commandline parameter
ID = args.ID
repeats = args.repeats
datapath = args.datapath
weight = args.weight
trial_num = args.trial_num

#----- shared paramaters -----
lickThres = int((args.lickThres/5)*1024)
mode = args.mode
punish = args.punish
lcount = args.lcount
rewardCond =args.rewardCond


"""
--------------------------------------------------------------------
END Arguments
--------------------------------------------------------------------
"""

def menu():
    """
    Reads the characters in the buffer and modifies the program
    parameters accordingly
    """
    c = "\x00"
    
    global punish
    global lickThres
    global lcount
    global mode
    global rewardCond
    global comment
    
    while True:
        while m.kbhit():
            c = m.getch()
            if c == '\xe0': c = c + m.getch()
        
        #menu:::
        
            if c in ("\r"):
                return
            
            # Toggle condition
            elif c in ("\t"):
                if mode == "c": mode = "o"
                elif mode == "o": mode = "h"
                elif mode == "h": mode = "c"
                print "Training mode:\t%s" %mode
                
            elif c in ("C","c"): #m,Ctrl-m
                comment = raw_input("Comment: ")
                log.write("Comment:\t%s\n" %comment)
                print "Choose...\r",
                
            elif c in '\xe0K':
                rewardCond = 'L'
                print "rewardCond:\t%s" %rewardCond
            
            elif c in '\xe0M':
                rewardCond = 'R'
                print "rewardCond:\t%s" %rewardCond
            
            elif c in ('\xe0P', '\xe0H'):
                rewardCond = '-'
                print "rewardCond:\t", rewardCond
            
            # Toggle punishment
            elif c in ("P", "p", "\x10"):
                punish = not punish
                print "Punish for wrong lick:\t%s" %punish
                log.write("Punish for wrong lick:\t%s\n" %punish)
                   
            # adjust minLickCount
            elif c in ("[", "{"):
                lcount -= 1
                print "minLickCount: %3d\r" %lcount,
            
            elif c in ("]", "}"):
                lcount += 1
                print "minLickCount: %3d\r" %lcount,
                
            elif c in ("|", "\\"):
                print "minLickCount: %3d\r" %lcount,

            # update lickThreshold....
            elif c in (",<"):
                lickThres -= 25
                print "lickThres: %4d .... %5.2f V\r" %(lickThres, (lickThres / 1024)*5),
            
            elif c in (".>"):
                lickThres += 25
                print "lickThres: %4d .... %5.2f V\r" %(lickThres, (lickThres / 1024)*5),
                
            elif c in ("/?"):
                print "lickThres: %4d .... %5.2f V\r" %(lickThres, (lickThres / 1024)*5),
            
            else:
                print "-----------------------------"
                print "options    :"
                print "  ...   P  : Punish"
                print "  ...   < >: lick threshold" 
                print "  ...   ?  : show threshold" 
                print "  ...   [ ]: lickcount"
                print "  ...   \\  : show lickcount" 
                print "  ...   tab: toggle mode"
                print "-----------------------------"
        
        
def colour (x, fc = color.Fore.WHITE, bc = color.Back.BLACK, style = color.Style.NORMAL):
    return "%s%s%s%s%s" %(fc, bc, style, x , color.Style.RESET_ALL)

def timenow():
    """provides the current time string in the form `HH:MM:SS`"""
    return datetime.datetime.now().time().strftime('%H:%M:%S')      
      
def today():
    """provides today's date as a string in the form YYMMDD"""
    return datetime.date.today().strftime('%y%m%d')

def Serial_monitor(logfile, show = True):
    
    line = ser.readline()
    
    if line:
        
        fmt_line = "%s\t%s\t%s\t%s" %(timenow(), port, ID, line.strip())
        
        if line.startswith("#"): 
            fmt_line = "#" + fmt_line
            if verbose: print colour(fmt_line, fc.CYAN, style = Style.BRIGHT)
        
        elif show: 
            if line.startswith("port") == False:
                print colour("%s\t%s\t%s" %(timenow(), port, ID), fc.WHITE),
                print colour(line.strip(), fc.YELLOW, style =  Style.BRIGHT)
            
        logfile.write(fmt_line + "\n")
        
    return line

def update_bbox(params, trial_df):
    """
    Communicates the contents of the dict `params` through
    the serial communications port. 
    
    data is sent in the form: `dict[key] = value`  --> `key:value`
    
    trail_df dictionary is updated to include the parameters 
    received from the arduino
    """
    
    for k in params.keys():
    
        print fc.YELLOW, k, 
        ser.writelines("%s:%s" %(k, params[k]))
        if verbose: print "%s:%s" %(k, params[k])
        
        time.sleep(0.2)
        
        while ser.inWaiting():

            line = Serial_monitor(log, False).strip()

            if line[0] != "#" and line[0] != "-":
                var, val = line.split(":\t")
                trial_df[var] = num(val)
                if var == k:
                    print  fc.GREEN, "\r", var, val, Style.RESET_ALL , "\r",
                else:
                    print  fc.RED, "\r", var, val, Style.RESET_ALL 
                    quit()
                
    return trial_df

def create_datapath(DATADIR = "", date = today()):
    """
    
    """
    
    if not DATADIR: DATADIR = os.path.join(os.getcwd(), date)
    else: DATADIR = os.path.join(DATADIR, date)
    
    if not os.path.isdir(DATADIR):
        os.makedirs((DATADIR))
    
    print colour("datapath:\t", fc = fc.GREEN, style=Style.BRIGHT),
    print colour(DATADIR, fc = fc.GREEN, style=Style.BRIGHT)
    
    return DATADIR        
  
def create_logfile(DATADIR = "", date = today()):
    """
    
    """

    filename = "%s_%s_%s.log" %(port,ID,date)
    logfile = os.path.join(DATADIR, filename)
    print colour("Saving log in:\t", fc = fc.GREEN, style=Style.BRIGHT),
    print colour("./$datapath$/%s" %filename, fc = fc.GREEN, style=Style.BRIGHT)
    
    return logfile
                    
def init_serialport(port, logfile = None):
    """
    Open communications with the arduino;
    quits the program if no communications are 
    found on port.
    
    If there are communications the script
    waits 500 ms then reads all incoming
    lines from the Serial port. These two
    lines include the arduino code version 
    and a string that says the arduino is online
    """
    
    ser = serial.Serial()
    ser.baudrate = 115200
    ser.timeout = 1
    ser.port = port

    try: 
        ser.open()
        print colour("\nContact", fc.GREEN, style = Style.BRIGHT)
        
    except serial.serialutil.SerialException: 
        print colour("No communications on %s" %port, fc.RED, style = Style.BRIGHT)
        sys.exit(0)
    
    #IDLE while Arduino performs it's setup functions
    print "\nAWAITING DISPATCH: ",
    
    t = 0
    while not ser.inWaiting():
        print "\rAWAITING DISPATCH: ", t, "\r",
        t += 1
    
    print "\r         DISPATCH: ", t
    
    # Buffer for 500 ms to let Arduino finish it's setup
    time.sleep(.5)
    # Log the debug info for the setup
    while ser.inWaiting(): 
        Serial_monitor(logfile, True)

    return ser
    
"""
---------------------------------------------------------------------
MAIN FUNCTION HERE
---------------------------------------------------------------------
"""    

color.init()

datapath = create_datapath(datapath) #appends todays date to the datapath
logfile = create_logfile(datapath) #creates a filepath for the logfile

#make a unique filename
_ = 0
df_file = '%s/%s_%s_%03d.csv' %(datapath, ID, today(), _)
while os.path.isfile(df_file):
    _ += 1
    df_file = '%s/%s_%s_%03d.csv' %(datapath, ID, today(), _)

comment = ""

try:
    #open a file to save data in
    with open(logfile, 'a') as log:
        #open the communications line
        ser = init_serialport(port, logfile = log)

        # loop for r repeats
        for r in xrange(repeats):
            
            print colour("BLOCK:\t%02d" %r, 
                fc.MAGENTA, style = Style.BRIGHT)
            
            # create an empty dictionary to store data in
            trial_df = {
                'trial_num' : trial_num,
                'WaterPort[0]': 0,
                'WaterPort[1]': 0,
                'ID' : ID,
                'manfreq' : manfreq,
                'weight' : weight,
                'block' : r,
                'comment' : comment,
            }
           
            
            #checks the keys pressed during last iteration
            #adjusts options accordingly
            if m.kbhit():
                menu()
                
            trial_df['comment'] = comment
            
            if rewardCond not in ('L', 'R'):
                rewardCond = ('L', 'R')[random.randint(0,1)]
            
            #THE HANDSHAKE
            # send all current parameters to the arduino box to run the trial
            params = {
                        'rewardCond'        : rewardCond,
                        'mode'              : mode,
                        'lickThres'         : lickThres,
                        'break_wrongChoice' : num(punish),
                        'minlickCount'      : lcount,
            }
            
            trial_df = update_bbox(params, trial_df)
            
            print colour("C:", params['rewardCond'], 
                            fc.MAGENTA, style = Style.BRIGHT),
                              
            #print colour("%s  GO!\r" %timenow(), fc.GREEN, style=Style.BRIGHT),
                
            trial_df['time'] = timenow()
            
            # Send the literal GO symbol
            ser.write("GO")
            
            line = Serial_monitor(log, show = verbose).strip()
            
            while line.strip() != "-- Status: Ready --":
                
                line = Serial_monitor(log, False).strip()
                if line:
                    if line[0] != "#" and line[0] != "-":
                        var, val = line.split(":\t")
                        val = num(val)
                        trial_df[var] = val
                        
            # partitions lick responses into three handy numbers each

            
            for k in trial_df.keys():
                if type(trial_df[k]) == list: trial_df[k] = trial_df[k][0]
           
            """
            #Save the data to a data frame / Save to a file
            """
                
            with open(df_file, 'w') as datafile:
                
                trial_df = pd.DataFrame(trial_df, index=[trial_num])
                
                try: 
                    df = df.append(trial_df, ignore_index = True)
                except NameError:
                    df = trial_df
                
                df['correct'] = df.response.str.isupper()
                df['miss'] = df.response[df.rewardCond != 'N'] == '-'
                df['wrong'] = df.response[df.rewardCond != 'N'].str.islower()
                
                hits = df.correct.cumsum()
                hit_L = df.correct[df.response == 'L'].cumsum()
                hit_R = df.correct[df.response == 'R'].cumsum()
                
                cumWater = df['WaterPort[0]'].cumsum() + df['WaterPort[1]'].cumsum()
                
                df['hits'] =  hits
                df['hit_L'] = hit_R
                df['hit_R'] = hit_L
                
                df['cumWater'] = cumWater               

                df.to_csv(datafile)
            
            #Print the important data and coloured code for hits / misses
            
            print Style.BRIGHT, '\r',
            
            
            table = {
                    'trial_num' : 't', 
                    'mode': 'mode', 
                    'rewardCond': 'rewCond', 
                    'response': 'response', 
                    'count[0]':'L', 
                    'count[1]': 'R', 
                    'WaterPort[0]': 'waterL', 
                    'WaterPort[1]': 'waterR',
                    'OFF[0]' : 'off0', 
                    'OFF[1]': 'off1',
            }
            
            for k in ('trial_num' , 'mode', 'rewardCond', 'response', 'count[0]', 'count[1]', 
                            'WaterPort[0]', 'WaterPort[1]', 'OFF[0]', 'OFF[1]',):
                
                if df.correct.iloc[-1]:
                    print '%s%s:%s%4s' %(fc.WHITE, table[k], fc.GREEN, str(trial_df[k].iloc[-1]).strip()),
                elif df.miss.iloc[-1]:
                    print '%s%s:%s%4s' %(fc.WHITE, table[k], fc.YELLOW, str(trial_df[k].iloc[-1]).strip()),
                else:
                    print '%s%s:%s%4s' %(fc.WHITE, table[k],fc.RED, str(trial_df[k].iloc[-1]).strip()),
            print '\r', Style.RESET_ALL
            
            #calculate percentage success
            
            print "\r", 100 * " ", "\r                ", #clear the line 
            
            hits = df.correct.sum() / df.ID.count()
            
            if df.ID[df.rewardCond.isin(['L','B'])].count():
                 hit_L = df.correct[df.response == 'L'].sum() / df.ID[df.rewardCond.isin(['L','B'])].count()
            else: hit_L = float('nan')
            
            if df.ID[df.rewardCond.isin(['R','B'])].count():
                 hit_R = df.correct[df.response == 'R'].sum() / df.ID[df.rewardCond.isin(['R','B'])].count()
            else: hit_R = float('nan')
            
            if df.ID[df.rewardCond != 'N'].count():
                misses = (df.miss.sum() / df.ID[df.rewardCond != 'N'].count())*100
            else: misses = float('nan')
            
            wrong = (df.wrong.sum() / df.ID.count())*100
            
            misses = na_printr(misses)
            wrong = na_printr(wrong)
            hits =  na_printr(hits*100)
            hit_L = na_printr(hit_L*100)
            hit_R = na_printr(hit_R*100)
            cumWater = df['WaterPort[0]'].sum() + df['WaterPort[1]'].sum()
                            
            print colour("hits:%03s%%  misses:%0s%%  wrong:%03s%%  R:%03s%%  L:%03s%%  Count:%4d  Water:%3d           " %(hits, misses, wrong, hit_R, hit_L, df.ID.count(), cumWater),
                            fc = fc.YELLOW, bc = bc.BLUE, style = Style.BRIGHT), '\r',
            
            comment = ""
            trial_num += 1
            
            ITI = random.uniform(args.ITI[0], args.ITI[1])
            time.sleep(ITI)
        
except KeyboardInterrupt:

   
    try:
        print "attempting to create DataFrame"
        trial_df = pd.DataFrame(trial_df, index=[trial_num])
        
        try: 
            df = df.append(trial_df, ignore_index = True)
        except NameError:
            df = trial_df
        
        df['correct'] = df.response.str.isupper()
        df['miss'] = df.response[df.rewardCond != 'N'] == '-'
        df['wrong'] = df.response[df.rewardCond != 'N'].str.islower()
        
        hits = df.correct.cumsum()
        hit_L = df.correct[df.response == 'L'].cumsum()
        hit_R = df.correct[df.response == 'R'].cumsum()
        
        cumWater = df['WaterPort[0]'].cumsum() + df['WaterPort[1]'].cumsum()
        
        df['hits'] =  hits
        df['hit_L'] = hit_R
        df['hit_R'] = hit_L
        
        df['cumWater'] = cumWater               

        df.to_csv(df_file)
    except NameError:
        print "unable to create trial_df does not exist"
    except AttributeError:
        df.to_csv(df_file)
        print "saved df"

    print "Closing", port
    sys.exit(0)