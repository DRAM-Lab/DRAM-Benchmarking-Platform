* Id-Vg sweep Vds=0.4050V
* Model: VCT_082 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_082.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.405000
Vg g 0 0
.dc Vg 0 0.810000 0.004050
.print dc i(Vd)
.measure dc ion FIND i(Vd) WHEN v(g)=0.810000
.measure dc ioff FIND i(Vd) WHEN v(g)=0
.end
