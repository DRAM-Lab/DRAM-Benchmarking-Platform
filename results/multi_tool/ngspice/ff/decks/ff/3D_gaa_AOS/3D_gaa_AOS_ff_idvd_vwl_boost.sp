* Id-Vd sweep Vgs=0.9487V
* Model: 3D_gaa_AOS | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_AOS_ngspice_46e9cdac6afc.inc'
Nn1 d g s s nfet L=4.000e-08 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0
Vg g 0 0.948750
.dc Vd 0 0.825000 0.008250
.print dc i(Vd) v(d)
* Ron extracted from DC log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
