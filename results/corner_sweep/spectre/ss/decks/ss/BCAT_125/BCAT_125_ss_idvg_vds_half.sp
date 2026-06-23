* Id-Vg sweep Vds=0.3825V
* Model: BCAT_125 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'
Vb b 0 0
Mn1 d g s b nfet l=1.200e-07 nfin=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vd d 0 0.382500
Vg g 0 0
.dc Vg 0 0.765000 0.003825
.print dc i(Vd)
.measure dc ion FIND i(Vd) WHEN v(g)=0.765000
.measure dc ioff FIND i(Vd) WHEN v(g)=0
.end
