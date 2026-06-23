* WL switching transient
* Model: 3D_gaa_Si | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_Si_ngspice_43e1c1d004a7.inc'
Nn1 d g s s nfet L=1.000e-07 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vd d 0 0.412500
Vg g 0 PWL(0 0 1n 0 2n 0.825000 10n 0.825000)
.tran 0.1n 20n
.print tran v(g) i(Vg)
* esw integrated from transient log in post-processing

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
