* Mini-array N=8 layout
* Model: 3D_gaa_Si | Corner: ff
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/3D_gaa_Si_ngspice_43e1c1d004a7.inc'

* Layout BL @ fpitch: Rmetal=1.833 Ohm/pitch, Rcontact=5.455 Ohm, Cmetal=7.333 fF/pitch
* Csa=11 fF, Cfar=3.667 fF, Cwl=0.7333 fF/cell
Vpre pre 0 dc 0.412500
Rpre pre bl0 100e6
Csa bl0 0 1.100000e-14
Vs s 0 0


Cmetal0 bl0 0 7.333333e-15
Rct0 bl0 bltap0 5.45455
Cwl0 bl0 wl0 7.333333e-16
Rmetal0 bl0 bl1 1.83333
Cmetal1 bl1 0 7.333333e-15
Rct1 bl1 bltap1 5.45455
Cwl1 bl1 wl1 7.333333e-16
Rmetal1 bl1 bl2 1.83333
Cmetal2 bl2 0 7.333333e-15
Rct2 bl2 bltap2 5.45455
Cwl2 bl2 wl2 7.333333e-16
Rmetal2 bl2 bl3 1.83333
Cmetal3 bl3 0 7.333333e-15
Rct3 bl3 bltap3 5.45455
Cwl3 bl3 wl3 7.333333e-16
Rmetal3 bl3 bl4 1.83333
Cmetal4 bl4 0 7.333333e-15
Rct4 bl4 bltap4 5.45455
Cwl4 bl4 wl4 7.333333e-16
Rmetal4 bl4 bl5 1.83333
Cmetal5 bl5 0 7.333333e-15
Rct5 bl5 bltap5 5.45455
Cwl5 bl5 wl5 7.333333e-16
Rmetal5 bl5 bl6 1.83333
Cmetal6 bl6 0 7.333333e-15
Rct6 bl6 bltap6 5.45455
Cwl6 bl6 wl6 7.333333e-16
Rmetal6 bl6 bl7 1.83333
Cmetal7 bl7 0 7.333333e-15
Rct7 bl7 bltap7 5.45455
Cwl7 bl7 wl7 7.333333e-16
Cfar bl7 0 3.666667e-15
Vwl0 wl0 0 PWL(0 0 1n 0 2n 0.825000 25n 0.825000)
Vplate0 plate0 0 0
Nn0 bltap0 wl0 cell0 s nfet L=1.000e-07 NFIN=1
Ccell0 cell0 plate0 2.000000e-14
Vwl1 wl1 0 0
Vplate1 plate1 0 0.412500
Nn1 bltap1 wl1 cell1 s nfet L=1.000e-07 NFIN=1
Ccell1 cell1 plate1 2.000000e-14
Vwl2 wl2 0 0
Vplate2 plate2 0 0.412500
Nn2 bltap2 wl2 cell2 s nfet L=1.000e-07 NFIN=1
Ccell2 cell2 plate2 2.000000e-14
Vwl3 wl3 0 0
Vplate3 plate3 0 0.412500
Nn3 bltap3 wl3 cell3 s nfet L=1.000e-07 NFIN=1
Ccell3 cell3 plate3 2.000000e-14
Vwl4 wl4 0 0
Vplate4 plate4 0 0.412500
Nn4 bltap4 wl4 cell4 s nfet L=1.000e-07 NFIN=1
Ccell4 cell4 plate4 2.000000e-14
Vwl5 wl5 0 0
Vplate5 plate5 0 0.412500
Nn5 bltap5 wl5 cell5 s nfet L=1.000e-07 NFIN=1
Ccell5 cell5 plate5 2.000000e-14
Vwl6 wl6 0 0
Vplate6 plate6 0 0.412500
Nn6 bltap6 wl6 cell6 s nfet L=1.000e-07 NFIN=1
Ccell6 cell6 plate6 2.000000e-14
Vwl7 wl7 0 0
Vplate7 plate7 0 0.412500
Nn7 bltap7 wl7 cell7 s nfet L=1.000e-07 NFIN=1
Ccell7 cell7 plate7 2.000000e-14
.ic v(bl0)=0.412500 v(bl1)=0.412500 v(bl2)=0.412500 v(bl3)=0.412500 v(bl4)=0.412500 v(bl5)=0.412500 v(bl6)=0.412500 v(bl7)=0.412500 v(cell0)=0
.tran 0.05n 25n
.print tran v(bl0) v(bl7) i(Vpre)
.measure tran t_bl_settle FIND time WHEN v(bl0)=0.408375 CROSS=1 FROM=2n TO=25n
.measure tran i_bl_leak AVG i(Vpre) FROM=15n TO=25n

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
