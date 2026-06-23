* 1T1C Ccell=20.0fF
* Model: 3D_gaa_Si | Corner: hot
.option gmin=1e-20 post=2 measdgt=8
.temp 85.0
.include 'build/spectre_compat/3D_gaa_Si_spectre_43e1c1d004a7.inc'

* High-Z BL precharge (BL at Vdd/2, floating during read)
* Write 2-7 ns (plate=Vdd), hold with plate=Vdd/2, read WL 12-22 ns
Vpre pre 0 dc 0.375000
Rpre pre bl 100e6
Vwl wl 0 PWL(0 0 11n 0 12n 0.750000 22n 0.750000 23n 0 40n 0)
Vpl plate 0 PWL(0 0 1n 0 2n 0.750000 7n 0.750000 7.1n 0.375000 40n 0.375000)
Vs s 0 0
Mn1 bl wl cell s nfet l=1.000e-07 nfin=1
Ccell cell plate 2.000000e-14
.ic v(bl)=0.375000 v(cell)=0
.tran 0.05n 40n
.print tran v(cell) v(bl) i(Vpre)
.measure tran t_write FIND time WHEN v(cell)=0.675000 CROSS=1 FROM=1n TO=10n
.measure tran t_read FIND time WHEN v(cell)=0.375000 CROSS=1 FROM=12n TO=23n
.measure tran i_hold AVG i(Vpre) FROM=25n TO=35n
.measure tran q_read INTEG i(Vpre) FROM=12n TO=22n
.end
