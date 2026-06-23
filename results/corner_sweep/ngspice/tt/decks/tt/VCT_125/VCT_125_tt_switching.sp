* WL switching transient
* Model: VCT_125 | Corner: tt
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/VCT_125_ngspice_7461669b2dff.inc'
Nn1 d g s s nfet L=2.400e-08 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.450000
Vg g 0 PWL(0 0 1n 0 2n 0.900000 10n 0.900000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
* esw integrated from transient log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
