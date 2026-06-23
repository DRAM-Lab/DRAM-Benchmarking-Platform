* Id-Vd sweep Vgs=0.8797V
* Model: BCAT_125 | Corner: ss_125
.option gmin=1e-20 post=2 measdgt=8
.temp 125.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/BCAT_125_ngspice_ddaf6b557280.inc'
Vb b 0 0
Nn1 d g s b nfet L=1.200e-07 NFIN=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vd d 0 0
Vg g 0 0.879750
.dc Vd 0 0.765000 0.007650
.print dc i(Vd) v(d)
* Ron extracted from DC log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
