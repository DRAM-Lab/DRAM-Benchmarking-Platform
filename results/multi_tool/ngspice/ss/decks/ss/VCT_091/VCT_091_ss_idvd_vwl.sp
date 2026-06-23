* Id-Vd sweep Vgs=0.8100V
* Model: VCT_091 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/VCT_091_ngspice_eb4e6209433d.inc'
Nn1 d g s s nfet L=2.400e-08 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0
Vg g 0 0.810000
.dc Vd 0 0.810000 0.008100
.print dc i(Vd) v(d)
* Ron extracted from DC log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
