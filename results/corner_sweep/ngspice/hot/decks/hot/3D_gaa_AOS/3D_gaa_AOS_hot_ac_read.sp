* Capacitance (transient step)
* Model: 3D_gaa_AOS | Corner: hot
.option gmin=1e-20 post=2 measdgt=8
.temp 85.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_AOS_ngspice_46e9cdac6afc.inc'
Nn1 d g s s nfet L=4.000e-08 NFIN=1
* Bulk reference for bulkmod=0
* Bulk net tied to: s

Vs s 0 0
Vg g 0 PWL(0 0.750000 1n 0.750000 1.01n 0.751000)
Vd d 0 PWL(0 0.375000 1n 0.375000 1.01n 0.376000)
.tran 0.001n 5n
.measure tran qg INTEG i(Vg) FROM=1.01n TO=3n
.measure tran qd INTEG i(Vd) FROM=1.01n TO=3n
* cgg/cgd derived from qg/qd in post-processing (dv=0.001000 V)

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
