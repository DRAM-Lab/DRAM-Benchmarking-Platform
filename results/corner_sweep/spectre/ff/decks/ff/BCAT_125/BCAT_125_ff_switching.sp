* WL switching transient
* Model: BCAT_125 | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'
Vb b 0 0
Mn1 d g s b nfet l=1.200e-07 nfin=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vd d 0 0.467500
Vg g 0 PWL(0 0 1n 0 2n 0.935000 10n 0.935000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
.measure tran esw INTEG 'v(g)*i(Vg)' FROM=0 TO=20n
.end
