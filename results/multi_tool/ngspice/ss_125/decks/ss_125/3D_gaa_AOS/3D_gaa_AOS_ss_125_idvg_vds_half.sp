* Id-Vg sweep Vds=0.3375V
* Model: 3D_gaa_AOS | Corner: ss_125
.option gmin=1e-20 post=2 measdgt=8
.temp 125.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_AOS_ngspice_46e9cdac6afc.inc'
Nn1 d g s s nfet L=4.000e-08 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.337500
Vg g 0 0
.dc Vg 0 0.675000 0.003375
.print dc i(Vd)
.measure dc ion MIN i(Vd)
.measure dc ioff FIND i(Vd) AT=0

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
