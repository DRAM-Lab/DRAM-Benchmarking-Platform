* WL switching transient
* Model: BCAT_125 | Corner: tt
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/BCAT_125_ngspice_ddaf6b557280.inc'
Vb b 0 0
Nn1 d g s b nfet L=1.200e-07 NFIN=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vd d 0 0.425000
Vg g 0 PWL(0 0 1n 0 2n 0.850000 10n 0.850000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
* esw integrated from transient log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
