* Id-Vg sweep Vds=0.8250V
* Model: 3D_gaa_Si | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_Si_ngspice_43e1c1d004a7.inc'
Nn1 d g s s nfet L=1.000e-07 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.825000
Vg g 0 0
.dc Vg 0 0.825000 0.004125
.print dc i(Vd)
.measure dc ion MIN i(Vd)
.measure dc ioff FIND i(Vd) AT=0

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
