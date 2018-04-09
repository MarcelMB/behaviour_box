void init_trial (byte trial_code) {
    // set the dynamic variables based on the trial code
    go_trial   = (trial_code >> 2) & 1;
    audit_stim = (trial_code >> 1) & 1;
    somat_stim = (trial_code >> 0) & 1;

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
    t = t_since(t_init);

    // wait
    ActiveDelay(stimONSET - noLickDUR, false);
    t = t_since(t_init);
    if (t <= stimONSET) {
      nolickcount += ActiveDelay(stimONSET - t, noLickDUR?1:0);
    }

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

    loggedWrite(lightPin, light);
    ActiveDelay(200, false);
    TrialStimulus();
    t = t_since(t_init);

    /* -----------------------------------------------------------------------
    ||                         POST STIM DELAY
    ++-----------------------------------------------------------------------*/

    ActiveDelay(respDEL, false);

    /* -----------------------------------------------------------------------
    ||                        RESPONSE PERIOD
    ++-----------------------------------------------------------------------*/

    conditional_tone(7000, 100);

    t = t_since(t_init);

    _lickcount += ActiveDelay(respDUR, lickTrigReward);

    if ((_lickcount >= lickCount)
        and ((t_since(t_init) - t) < respDUR)
        and lickTrigReward
        and go_trial
      ) {
      // keeps counting even if the reward was triggered already
        deliver_reward(1);
        response = 'H';
        ActiveDelay((respDUR - (t_since(t_init) - t)) , 0);
    }

    if (go_trial){
      if (_lickcount >= lickCount) {
          if (not reward){
              deliver_reward(1);
              response = 'H';
          }
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
    stimulus = true; //TODO replace withsomthing smarter
    if (senseLick()) {
        loggedWrite(bulbTrig, HIGH);
        TrialStimulus();
        deliver_reward(1);
        Send_stop();
        ActiveDelay(3500u, false);
        loggedWrite(bulbTrig, LOW);
    }
}
