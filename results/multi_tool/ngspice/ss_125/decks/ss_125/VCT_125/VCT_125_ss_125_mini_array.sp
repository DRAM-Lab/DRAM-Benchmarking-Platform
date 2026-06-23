* Mini-array N=8 layout
* Model: VCT_125 | Corner: ss_125
.option gmin=1e-20 post=2 measdgt=8
.temp 125.0
.include '/home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/inc_cache/VCT_125_ngspice_7461669b2dff.inc'

* Layout BL @ fpitch: Rmetal=5 Ohm/pitch, Rcontact=2 Ohm, Cmetal=20 fF/pitch
* Csa=30 fF, Cfar=10 fF, Cwl=2 fF/cell
Vpre pre 0 dc 0.405000
Rpre pre bl0 100e6
Csa bl0 0 3.000000e-14
Vs s 0 0


Cmetal0 bl0 0 2.000000e-14
Rct0 bl0 bltap0 2
Cwl0 bl0 wl0 2.000000e-15
Rmetal0 bl0 bl1 5
Cmetal1 bl1 0 2.000000e-14
Rct1 bl1 bltap1 2
Cwl1 bl1 wl1 2.000000e-15
Rmetal1 bl1 bl2 5
Cmetal2 bl2 0 2.000000e-14
Rct2 bl2 bltap2 2
Cwl2 bl2 wl2 2.000000e-15
Rmetal2 bl2 bl3 5
Cmetal3 bl3 0 2.000000e-14
Rct3 bl3 bltap3 2
Cwl3 bl3 wl3 2.000000e-15
Rmetal3 bl3 bl4 5
Cmetal4 bl4 0 2.000000e-14
Rct4 bl4 bltap4 2
Cwl4 bl4 wl4 2.000000e-15
Rmetal4 bl4 bl5 5
Cmetal5 bl5 0 2.000000e-14
Rct5 bl5 bltap5 2
Cwl5 bl5 wl5 2.000000e-15
Rmetal5 bl5 bl6 5
Cmetal6 bl6 0 2.000000e-14
Rct6 bl6 bltap6 2
Cwl6 bl6 wl6 2.000000e-15
Rmetal6 bl6 bl7 5
Cmetal7 bl7 0 2.000000e-14
Rct7 bl7 bltap7 2
Cwl7 bl7 wl7 2.000000e-15
Cfar bl7 0 1.000000e-14
Vwl0 wl0 0 PWL(0 0 1n 0 2n 0.810000 25n 0.810000)
Vplate0 plate0 0 0
Nn0 bltap0 wl0 cell0 s nfet L=2.400e-08 NFIN=1
Ccell0 cell0 plate0 2.000000e-14
Vwl1 wl1 0 0
Vplate1 plate1 0 0.405000
Nn1 bltap1 wl1 cell1 s nfet L=2.400e-08 NFIN=1
Ccell1 cell1 plate1 2.000000e-14
Vwl2 wl2 0 0
Vplate2 plate2 0 0.405000
Nn2 bltap2 wl2 cell2 s nfet L=2.400e-08 NFIN=1
Ccell2 cell2 plate2 2.000000e-14
Vwl3 wl3 0 0
Vplate3 plate3 0 0.405000
Nn3 bltap3 wl3 cell3 s nfet L=2.400e-08 NFIN=1
Ccell3 cell3 plate3 2.000000e-14
Vwl4 wl4 0 0
Vplate4 plate4 0 0.405000
Nn4 bltap4 wl4 cell4 s nfet L=2.400e-08 NFIN=1
Ccell4 cell4 plate4 2.000000e-14
Vwl5 wl5 0 0
Vplate5 plate5 0 0.405000
Nn5 bltap5 wl5 cell5 s nfet L=2.400e-08 NFIN=1
Ccell5 cell5 plate5 2.000000e-14
Vwl6 wl6 0 0
Vplate6 plate6 0 0.405000
Nn6 bltap6 wl6 cell6 s nfet L=2.400e-08 NFIN=1
Ccell6 cell6 plate6 2.000000e-14
Vwl7 wl7 0 0
Vplate7 plate7 0 0.405000
Nn7 bltap7 wl7 cell7 s nfet L=2.400e-08 NFIN=1
Ccell7 cell7 plate7 2.000000e-14
.ic v(bl0)=0.405000 v(bl1)=0.405000 v(bl2)=0.405000 v(bl3)=0.405000 v(bl4)=0.405000 v(bl5)=0.405000 v(bl6)=0.405000 v(bl7)=0.405000 v(cell0)=0
.tran 0.05n 25n
.print tran v(bl0) v(bl7) i(Vpre)
.measure tran t_bl_settle FIND time WHEN v(bl0)=0.400950 CROSS=1 FROM=2n TO=25n
.measure tran i_bl_leak AVG i(Vpre) FROM=15n TO=25n

.control
pre_osdi /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/build/ngspice_osdi/bsimcmg.osdi
.endc
.end
