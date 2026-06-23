* GIDL / retention leakage
* Model: VCT_082 | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_082.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vg g 0 0
Vd d 0 0.990000
.op
.print dc i(Vd) i(Vg)
.measure dc igidl FIND i(Vd)
.end
