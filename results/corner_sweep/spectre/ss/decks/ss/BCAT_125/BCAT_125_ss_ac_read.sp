* Capacitance (transient step)
* Model: BCAT_125 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'
Vb b 0 0
Mn1 d g s b nfet l=1.200e-07 nfin=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vg g 0 PWL(0 0.765000 1n 0.765000 1.01n 0.766000)
Vd d 0 PWL(0 0.382500 1n 0.382500 1.01n 0.383500)
.tran 0.001n 5n
.measure tran qg INTEG i(Vg) FROM=1.01n TO=3n
.measure tran qd INTEG i(Vd) FROM=1.01n TO=3n
.measure tran cgg param='abs(qg)/0.001000'
.measure tran cgd param='abs(qd)/0.001000'
.end
