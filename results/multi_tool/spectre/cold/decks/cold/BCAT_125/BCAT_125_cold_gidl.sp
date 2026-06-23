* GIDL / retention leakage
* Model: BCAT_125 | Corner: cold
.option gmin=1e-20 post=2 measdgt=8
.temp -40.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'
Vb b 0 0
Mn1 d g s b nfet l=1.200e-07 nfin=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vg g 0 0
Vd d 0 0.850000
.op
.print dc i(Vd) i(Vg)
.measure dc igidl FIND i(Vd)
.end
