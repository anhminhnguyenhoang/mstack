---- MODULE SearchLoop ----
EXTENDS Naturals
CONSTANTS Cands, CHECK_CORRECT, PLATEAU_STOP, PLATEAU
VARIABLES status, correct, misses, phase
vars == <<status, correct, misses, phase>>

Open == {c \in Cands : status[c] \in {"queued", "eligible"}}

Init == /\ status = [c \in Cands |-> "queued"]
        /\ correct = [c \in Cands |-> FALSE]
        /\ misses = 0
        /\ phase = "running"

Try(c) == /\ phase = "running"
          /\ c \in Open
          /\ \E ok, faster \in BOOLEAN :
               LET keep == faster /\ (ok \/ ~CHECK_CORRECT) IN
               /\ correct' = [correct EXCEPT ![c] = ok]
               /\ IF keep
                  THEN /\ status' = [d \in Cands |-> IF d = c THEN "kept"
                                                     ELSE IF status[d] = "retired" THEN "eligible"
                                                     ELSE status[d]]
                       /\ misses' = 0
                  ELSE /\ status' = [status EXCEPT ![c] = "retired"]
                       /\ misses' = misses + 1
          /\ UNCHANGED phase

Stop == /\ phase = "running"
        /\ (Open = {} \/ (PLATEAU_STOP /\ misses >= PLATEAU))
        /\ phase' = "stopped"
        /\ UNCHANGED <<status, correct, misses>>

Done == phase = "stopped" /\ UNCHANGED vars

Next == (\E c \in Cands : Try(c)) \/ Stop \/ Done

NeverKeepIncorrect == \A c \in Cands : status[c] = "kept" => correct[c]
StopOnlyWhenDone == phase = "stopped" => Open = {}

Spec == Init /\ [][Next]_vars
====
