* GIDL / retention leakage
* Model: 3D_gaa_Si | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'build/spectre_compat/3D_gaa_Si_spectre_43e1c1d004a7.inc'
Mn1 d g s s nfet l=1.000e-07 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vg g 0 0
Vd d 0 0.675000
.op
.print dc i(Vd) i(Vg)
.measure dc igidl FIND i(Vd)
.end
