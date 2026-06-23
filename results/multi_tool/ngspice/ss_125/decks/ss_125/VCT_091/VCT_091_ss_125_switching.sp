* WL switching transient
* Model: VCT_091 | Corner: ss_125
.option gmin=1e-20 post=2 measdgt=8
.temp 125.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/VCT_091_ngspice_eb4e6209433d.inc'
Nn1 d g s s nfet L=2.400e-08 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.405000
Vg g 0 PWL(0 0 1n 0 2n 0.810000 10n 0.810000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
* esw integrated from transient log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
