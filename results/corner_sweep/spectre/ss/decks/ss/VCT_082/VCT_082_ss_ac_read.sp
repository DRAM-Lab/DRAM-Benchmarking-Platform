* Capacitance (transient step)
* Model: VCT_082 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_082.inc'
Mn1 d g s s nfet l=2.400e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vg g 0 PWL(0 0.810000 1n 0.810000 1.01n 0.811000)
Vd d 0 PWL(0 0.405000 1n 0.405000 1.01n 0.406000)
.tran 0.001n 5n
.measure tran qg INTEG i(Vg) FROM=1.01n TO=3n
.measure tran qd INTEG i(Vd) FROM=1.01n TO=3n
.measure tran cgg param='abs(qg)/0.001000'
.measure tran cgd param='abs(qd)/0.001000'
.end
