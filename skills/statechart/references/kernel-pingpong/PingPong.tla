---- MODULE PingPong ----
EXTENDS Naturals
CONSTANTS NBUF, ITERS
Waves == {1, 2}
VARIABLES pc, it
vars == <<pc, it>>

Buf(w) == it[w] % NBUF

Init == pc = [w \in Waves |-> "load"] /\ it = [w \in Waves |-> 0]

StartWrite(w) == pc[w] = "load" /\ it[w] < ITERS
                 /\ pc' = [pc EXCEPT ![w] = "writing"] /\ UNCHANGED it
EndWrite(w)   == pc[w] = "writing" /\ pc' = [pc EXCEPT ![w] = "barrier"] /\ UNCHANGED it
Barrier       == (\A w \in Waves : pc[w] = "barrier")
                 /\ pc' = [u \in Waves |-> "reading"] /\ UNCHANGED it
EndRead(w)    == pc[w] = "reading"
                 /\ pc' = [pc EXCEPT ![w] = "load"] /\ it' = [it EXCEPT ![w] = it[w] + 1]
Done          == (\A w \in Waves : it[w] = ITERS) /\ UNCHANGED vars

Next == (\E w \in Waves : StartWrite(w) \/ EndWrite(w) \/ EndRead(w)) \/ Barrier \/ Done

NoOverwriteWhileRead ==
  \A v, w \in Waves : (v # w /\ pc[v] = "writing" /\ pc[w] = "reading") => Buf(v) # Buf(w)

Spec == Init /\ [][Next]_vars
====
