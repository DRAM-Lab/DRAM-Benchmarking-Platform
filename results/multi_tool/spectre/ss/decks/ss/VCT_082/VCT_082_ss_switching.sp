* WL switching transient
* Model: VCT_082 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_082.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.405000
Vg g 0 PWL(0 0 1n 0 2n 0.810000 10n 0.810000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
.measure tran esw INTEG 'v(g)*i(Vg)' FROM=0 TO=20n
.end
