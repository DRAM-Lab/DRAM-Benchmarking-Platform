* 1T1C Ccell=20.0fF
* Model: 3D_gaa_Si | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_Si_ngspice_43e1c1d004a7.inc'

* High-Z BL precharge (BL at Vdd/2, floating during read)
* Write 2-7 ns (plate=Vdd), hold with plate=Vdd/2, read WL 12-22 ns
Vpre pre 0 dc 0.412500
Rpre pre bl 100e6
Vwl wl 0 PWL(0 0 11n 0 12n 0.825000 22n 0.825000 23n 0 40n 0)
Vpl plate 0 PWL(0 0 1n 0 2n 0.825000 7n 0.825000 7.1n 0.412500 40n 0.412500)
Vs s 0 0
Nn1 bl wl cell s nfet L=1.000e-07 NFIN=1
Ccell cell plate 2.000000e-14
.ic v(bl)=0.412500 v(cell)=0
.tran 0.05n 40n
.print tran v(cell) v(bl) i(Vpre)
.measure tran t_write FIND time WHEN v(cell)=0.742500 CROSS=1 FROM=1n TO=10n
.measure tran t_read FIND time WHEN v(cell)=0.412500 CROSS=1 FROM=12n TO=23n
.measure tran i_hold AVG i(Vpre) FROM=25n TO=35n
.measure tran q_read INTEG i(Vpre) FROM=12n TO=22n

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
