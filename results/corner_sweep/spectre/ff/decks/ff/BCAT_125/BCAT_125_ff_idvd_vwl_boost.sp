* Id-Vd sweep Vgs=1.0753V
* Model: BCAT_125 | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'
Vb b 0 0
Mn1 d g s b nfet l=1.200e-07 nfin=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vd d 0 0
Vg g 0 1.075250
.dc Vd 0 0.935000 0.009350
.print dc i(Vd) v(d)
.measure dc ron param='abs(v(d)/i(Vd))'
.end
