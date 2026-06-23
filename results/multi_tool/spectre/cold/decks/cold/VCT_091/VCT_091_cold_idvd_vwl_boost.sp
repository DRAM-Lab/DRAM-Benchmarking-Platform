* Id-Vd sweep Vgs=1.0350V
* Model: VCT_091 | Corner: cold
.option gmin=1e-20 post=2 measdgt=8
.temp -40.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_091.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0
Vg g 0 1.035000
.dc Vd 0 0.900000 0.009000
.print dc i(Vd) v(d)
.measure dc ron param='abs(v(d)/i(Vd))'
.end
