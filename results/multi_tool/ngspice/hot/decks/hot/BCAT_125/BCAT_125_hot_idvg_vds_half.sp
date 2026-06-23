* Id-Vg sweep Vds=0.4250V
* Model: BCAT_125 | Corner: hot
.option gmin=1e-20 post=2 measdgt=8
.temp 85.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/BCAT_125_ngspice_ddaf6b557280.inc'
Vb b 0 0
Nn1 d g s b nfet L=1.200e-07 NFIN=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vd d 0 0.425000
Vg g 0 0
.dc Vg 0 0.850000 0.004250
.print dc i(Vd)
.measure dc ion MIN i(Vd)
.measure dc ioff FIND i(Vd) AT=0

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
