Sorry it's a mess,

I'm a Neuroscientist not a software engineer

This is code to run my experiments


#SerialController.py

1. The program starts
2. The program reads `config.tab` and `Frequencies.tab`,
    
    `config.tab` contains the details for a single run, 
    each line in the format `variablename : value`
    
    `Frequencies.tab` contains the block of frequencies that will be shuffled, in Hz. 
    The first line is a header with the title `frequency`, that gets ignored
    
2. The program opens communications with available serial port
    The program waits until it gets the arduino is active, and prints all output
    until the ready signal is transmitted. Which, because I played too much 
    command and conquer as a kid is `--Welcome Back Commander`
    
3. The program starts a block
4. The program shuffles the stimuli (frequencies list)

5. The program transmits the frequencies to the behaviour box,
    The dict `params` holds all parameters for a single trial (from `config.tab`)
    The condition values get updated; based on the frequencies being sent,
    all contents of `params` are transmitted to the behaviour controller.
    
6. The program prints the frequencies and the condition to the screen and a
   random timeout is started.
6. The program initiates a trial by sending a literal `"GO"` to the 
   behaviour box.
   - The behaviour box runs one trial, with the parameters set previously

7. The program records the output from behaviorCOMs into a
   dict, which later will be converted to a data frame for analysis.

8. The program repeats sending mode flags until all stimuli combinations have
   been run through.
   
TODO:

9. The program calculates d\`|any_stimuls; d\`|rising; d\`|falling







# Behaviour_box.ino

This program delivers sensory stimulation and opens water 
valve when the animal touches the licking sensor within a 
certain time window.

Setup connections:
------------------



|  DIGITAL  | output            | variable        |
| --------- | ----------------- | --------------- |
| pin 2     | recording trigger | `recTrig`       |
| pin 3     | stimulus          | `stimulusPin`   |
| pin 8     | speaker           | `tonePin`       |
| pin 7     | vacuum tube valve | `vacValve`      |
| pin 10    | left water valve  | `waterValve[0]` |
| pin 11    | right water valve | `waterValve[1]` |
| pin 13    | left  lick report | `lickRep[0]`    |
| pin 13    | right lick report | `lickRep[1]`    |
| --------- | ----------------- | --------------- |

| ANALOG    | input             |                 |
| --------- | ----------------- | --------------- |
| A0        | left  lick sensor | `lickSens[0]`   |
| A1        | right lick sensor | `lickSens[1]`   |
| --------- | ----------------- | --------------- |

Table: connections to lick controller
  
Start program:
--------------

The arduino program is a little complicated; but in principle a simple
setup. The main method is `runTrial` which on initialisation:

1. Waits a period of ms defined by `trial_delay`. In this period the timer counts
   up to zero; and the sensors detect licks. 10 ms before zero, a pulse is sent to
   the `recTrig` to trigger the recording
2. Next two periods of `ActiveDelay` are intialised in sequence. Two are used 
   so that if I decide the set a `noLickPer` time, I can have that come on a
   short time after the trigger. `ActiveDelay` has the condition `break_on_lick`
   as it's second argument. If `true` the program will exit the function before
   it reaches the time that it is set to delay until. **TODO** make it so that if
   `ActiveDelay` is broken the trial exits and prints `"#timeout initiated"` or
    equivalent, for the SerialController to parse.
3. Two stimuli are delivered, seperated by an `ActiveDelay` method.
4. After another `ActiveDelay` the program enters the `TrialReward` period, if
   `rewardCond` is not `'N'`, which stands for neither port giving water. During
   the `TrialReward` phase, if the `mode` is `c` then water is dispensed 
   immediately from the associated port.
5. The program delays again, and then exits the `runTrial` function. Resulting in
   the program sending the ready string to the Serial controller.

Trial intervals will randomized between 'minITI' and 'maxITI'. 
During a trial, the animal has to wait a stimulation without 
licking (no-lick period, 'nolickPer').
If it licks during no-lick period, the time of stimulation 
will be postponed by giving a time out (randomized between 
'minTimeOut' and 'maxTimeOut').
When a stimulation is delivered (stimulus duration: 'stimDur'), 
the animal need to respond (touch the sensor) within a certain 
time window ('crPer') to get a water reward.
Delayed lickig after the time window will not be rewarded. 
Opening duration of the water valve is defined by 'valveDur'.
A TTL trigger for recording will be delivered 
'baseLineTime' (1 s in default setting) before the stimulus.