* Id-Vd sweep Vgs=0.9900V
* Model: VCT_091 | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_091.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0
Vg g 0 0.990000
.dc Vd 0 0.990000 0.009900
.print dc i(Vd) v(d)
.measure dc ron param='abs(v(d)/i(Vd))'
.end
