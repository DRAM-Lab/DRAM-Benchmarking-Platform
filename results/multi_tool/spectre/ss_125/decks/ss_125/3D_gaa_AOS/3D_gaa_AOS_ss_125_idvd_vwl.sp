* Id-Vd sweep Vgs=0.6750V
* Model: 3D_gaa_AOS | Corner: ss_125
.option gmin=1e-20 post=2 measdgt=8
.temp 125.0
.include 'models/OpenDRAMmodelV1/models/access_tx/3D_gaa_AOS.inc'
Mn1 d g s s nfet l=4.000e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0
Vg g 0 0.675000
.dc Vd 0 0.675000 0.006750
.print dc i(Vd) v(d)
.measure dc ron param='abs(v(d)/i(Vd))'
.end
