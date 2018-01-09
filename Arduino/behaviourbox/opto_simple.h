void init_trial (byte trial_code) {
    // set the dynamic variables based on the trial code
    stimulus   = (trial_code >> 2) & 1;
    light_stim = (trial_code >> 1) & 1;
    light_resp = (trial_code >> 0) & 1;
    
    pick_duration();
}

void run_opto_trial() {

    // flush all output variables
    unsigned long t;  // the local time
    response = 0;     //
    N_to = 0;         //
    reward = 0;       //

    //tmp variables
    int nolickcount = 0;
    unsigned int _lickcount = 0;
    /* -----------------------------------------------------------------------
    ||                         START OF THE TRIAL
    ++-----------------------------------------------------------------------*/
    t_init = millis();
    loggedWrite(bulbTrig, HIGH);
    loggedWrite(lightPin, light_stim);

    
    t = t_since(t_init);

    // wait
    ActiveDelay(stimONSET - noLickDUR, false);
    t = t_since(t_init);
    if (t < stimONSET) {
      nolickcount += ActiveDelay(stimONSET - t, noLickDUR?1:0);
    }
    //t = t_since(t_init);

    // Break out on early lick
    if ((nolickcount > 0) and noLickDUR){
        response = 'e';
        loggedWrite(bulbTrig, LOW);
        Send_stop();
        return;
    }

    /* -----------------------------------------------------------------------
    ||                            STIMULUS
    ++-----------------------------------------------------------------------*/

    
    TrialStimulus();
    //loggedWrite(lightPin, LOW);
    t = t_since(t_init);

    /* -----------------------------------------------------------------------
    ||                         POST STIM DELAY
    ++-----------------------------------------------------------------------*/

    ActiveDelay(respDEL, false);

    /* -----------------------------------------------------------------------
    ||                        RESPONSE PERIOD
    ++-----------------------------------------------------------------------*/

    //loggedWrite(lightPin, light_resp);
    conditional_tone(7000, 100);

    t = t_since(t_init);

    _lickcount += ActiveDelay(respDUR, lickTrigReward);

    if ((t_since(t_init) - t) < respDUR) {
      // keeps counting even if the reward was triggered already
        deliver_reward(lickTrigReward and stimulus);
        response = 'H';
        ActiveDelay((respDUR - (t_since(t_init) - t)) , 0);
    }

    if (stimulus){
        if (_lickcount >= lickCount) {
            deliver_reward(response?0:1);
            response = 'H';
        }
        else {
            response = 'm';
        }
    }
    else {
        if (_lickcount >= lickCount) {
            response = 'f';
            punish(200);

            if (timeout) {
                N_to = Timeout(timeout); //count the number of timeouts
            }
        }
        else {
            response = 'R';
        }
    }

    loggedWrite(lightPin, LOW);

    /* -----------------------------------------------------------------------++
    ||                        POST RESPONSE BASELINE                          ||
    ++------------------------------------------------------------------------*/

    //continue trial till end (for the bulb trigger)
    t = t_since(t_init);
    if (t < trialDUR){
        ActiveDelay((trialDUR - t), 0);
    }

    loggedWrite(bulbTrig, LOW);
    /* -----------------------------------------------------------------------
    ||                             END TRIAL
    ++-----------------------------------------------------------------------*/
    //Send 4 null bytes to signal end of trial
    Send_stop();
    Send_stop();
    Send_stop();
    Send_stop();

    return;
}

void run_habituation(){
    // Check the lick sensor
    stimulus = true;
    if (senseLick()) {
        loggedWrite(bulbTrig, HIGH);
        TrialStimulus();
        deliver_reward(1);
        Send_stop();
        ActiveDelay(3500u, false);
        loggedWrite(bulbTrig, LOW);
    }
}
