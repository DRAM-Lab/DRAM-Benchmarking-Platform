* Capacitance (transient step)
* Model: BCAT_125 | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/BCAT_125_ngspice_ddaf6b557280.inc'
Vb b 0 0
Nn1 d g s b nfet L=1.200e-07 NFIN=1
* Bulk reference for bulkmod=1
* Bulk net tied to: b

Vs s 0 0
Vg g 0 PWL(0 0.935000 1n 0.935000 1.01n 0.936000)
Vd d 0 PWL(0 0.467500 1n 0.467500 1.01n 0.468500)
.tran 0.001n 5n
.measure tran qg INTEG i(Vg) FROM=1.01n TO=3n
.measure tran qd INTEG i(Vd) FROM=1.01n TO=3n
* cgg/cgd derived from qg/qd in post-processing (dv=0.001000 V)

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
