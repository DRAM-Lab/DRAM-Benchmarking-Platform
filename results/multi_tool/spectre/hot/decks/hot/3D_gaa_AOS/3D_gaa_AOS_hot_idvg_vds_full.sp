* Id-Vg sweep Vds=0.7500V
* Model: 3D_gaa_AOS | Corner: hot
.option gmin=1e-20 post=2 measdgt=8
.temp 85.0
.include 'models/OpenDRAMmodelV1/models/access_tx/3D_gaa_AOS.inc'
Mn1 d g s s nfet l=4.000e-08 nfin=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.750000
Vg g 0 0
.dc Vg 0 0.750000 0.003750
.print dc i(Vd)
.measure dc ion FIND i(Vd) WHEN v(g)=0.750000
.measure dc ioff FIND i(Vd) WHEN v(g)=0
.end
