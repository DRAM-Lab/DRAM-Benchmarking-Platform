* Id-Vg sweep Vds=0.9000V
* Model: VCT_091 | Corner: hot
.option gmin=1e-20 post=2 measdgt=8
.temp 85.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_091.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.900000
Vg g 0 0
.dc Vg 0 0.900000 0.004500
.print dc i(Vd)
.measure dc ion FIND i(Vd) WHEN v(g)=0.900000
.measure dc ioff FIND i(Vd) WHEN v(g)=0
.end
