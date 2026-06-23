* GIDL / retention leakage
* Model: 3D_gaa_AOS | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/3D_gaa_AOS.inc'
Mn1 d g s s nfet l=4.000e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vg g 0 0
Vd d 0 0.675000
.op
.print dc i(Vd) i(Vg)
.measure dc igidl FIND i(Vd)
.end
