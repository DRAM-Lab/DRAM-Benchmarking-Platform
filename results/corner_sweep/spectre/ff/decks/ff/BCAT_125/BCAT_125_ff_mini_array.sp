* Mini-array N=8 layout
* Model: BCAT_125 | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'

* Layout BL @ fpitch: Rmetal=3.5 Ohm/pitch, Rcontact=2.857 Ohm, Cmetal=14 fF/pitch
* Csa=21 fF, Cfar=7 fF, Cwl=1.4 fF/cell
Vpre pre 0 dc 0.467500
Rpre pre bl0 100e6
Csa bl0 0 2.100000e-14
Vs s 0 0

Vb b 0 0

Cmetal0 bl0 0 1.400000e-14
Rct0 bl0 bltap0 2.85714
Cwl0 bl0 wl0 1.400000e-15
Rmetal0 bl0 bl1 3.5
Cmetal1 bl1 0 1.400000e-14
Rct1 bl1 bltap1 2.85714
Cwl1 bl1 wl1 1.400000e-15
Rmetal1 bl1 bl2 3.5
Cmetal2 bl2 0 1.400000e-14
Rct2 bl2 bltap2 2.85714
Cwl2 bl2 wl2 1.400000e-15
Rmetal2 bl2 bl3 3.5
Cmetal3 bl3 0 1.400000e-14
Rct3 bl3 bltap3 2.85714
Cwl3 bl3 wl3 1.400000e-15
Rmetal3 bl3 bl4 3.5
Cmetal4 bl4 0 1.400000e-14
Rct4 bl4 bltap4 2.85714
Cwl4 bl4 wl4 1.400000e-15
Rmetal4 bl4 bl5 3.5
Cmetal5 bl5 0 1.400000e-14
Rct5 bl5 bltap5 2.85714
Cwl5 bl5 wl5 1.400000e-15
Rmetal5 bl5 bl6 3.5
Cmetal6 bl6 0 1.400000e-14
Rct6 bl6 bltap6 2.85714
Cwl6 bl6 wl6 1.400000e-15
Rmetal6 bl6 bl7 3.5
Cmetal7 bl7 0 1.400000e-14
Rct7 bl7 bltap7 2.85714
Cwl7 bl7 wl7 1.400000e-15
Cfar bl7 0 7.000000e-15
Vwl0 wl0 0 PWL(0 0 1n 0 2n 0.935000 25n 0.935000)
Vplate0 plate0 0 0
Mn0 bltap0 wl0 cell0 b nfet l=1.200e-07 nfin=1
Ccell0 cell0 plate0 2.000000e-14
Vwl1 wl1 0 0
Vplate1 plate1 0 0.467500
Mn1 bltap1 wl1 cell1 b nfet l=1.200e-07 nfin=1
Ccell1 cell1 plate1 2.000000e-14
Vwl2 wl2 0 0
Vplate2 plate2 0 0.467500
Mn2 bltap2 wl2 cell2 b nfet l=1.200e-07 nfin=1
Ccell2 cell2 plate2 2.000000e-14
Vwl3 wl3 0 0
Vplate3 plate3 0 0.467500
Mn3 bltap3 wl3 cell3 b nfet l=1.200e-07 nfin=1
Ccell3 cell3 plate3 2.000000e-14
Vwl4 wl4 0 0
Vplate4 plate4 0 0.467500
Mn4 bltap4 wl4 cell4 b nfet l=1.200e-07 nfin=1
Ccell4 cell4 plate4 2.000000e-14
Vwl5 wl5 0 0
Vplate5 plate5 0 0.467500
Mn5 bltap5 wl5 cell5 b nfet l=1.200e-07 nfin=1
Ccell5 cell5 plate5 2.000000e-14
Vwl6 wl6 0 0
Vplate6 plate6 0 0.467500
Mn6 bltap6 wl6 cell6 b nfet l=1.200e-07 nfin=1
Ccell6 cell6 plate6 2.000000e-14
Vwl7 wl7 0 0
Vplate7 plate7 0 0.467500
Mn7 bltap7 wl7 cell7 b nfet l=1.200e-07 nfin=1
Ccell7 cell7 plate7 2.000000e-14
.ic v(bl0)=0.467500 v(bl1)=0.467500 v(bl2)=0.467500 v(bl3)=0.467500 v(bl4)=0.467500 v(bl5)=0.467500 v(bl6)=0.467500 v(bl7)=0.467500 v(cell0)=0
.tran 0.05n 25n
.print tran v(bl0) v(bl7) i(Vpre)
.measure tran t_bl_settle FIND time WHEN v(bl0)=0.462825 CROSS=1 FROM=2n TO=25n
.measure tran i_bl_leak AVG i(Vpre) FROM=15n TO=25n
.end
