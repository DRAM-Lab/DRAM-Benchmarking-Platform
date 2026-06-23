* WL switching transient
* Model: 3D_gaa_Si | Corner: tt
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'build/spectre_compat/3D_gaa_Si_spectre_43e1c1d004a7.inc'
Mn1 d g s s nfet l=1.000e-07 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.375000
Vg g 0 PWL(0 0 1n 0 2n 0.750000 10n 0.750000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
.measure tran esw INTEG 'v(g)*i(Vg)' FROM=0 TO=20n
.end
