* Coupling read k=0.100 Ccell=20.0fF
* Model: VCT_125 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/VCT_125.inc'

* Multi-BL coupling victim read (victim = bl_sense, ref = blb_sense)
Vpre_left pre_left 0 dc 0.405000
Rpre_left pre_left n_left 100e6
Rbl_left n_left n_left_mid 50.000000
Cbl_left n_left_mid 0 2.000000e-13
Rseg_left n_left_mid bl_left 0.1
Vpre_victim pre_victim 0 dc 0.405000
Rpre_victim pre_victim n_victim 100e6
Rbl_victim n_victim n_victim_mid 50.000000
Cbl_victim n_victim_mid 0 2.000000e-13
Rseg_victim n_victim_mid bl_sense 0.1
Vpre_right pre_right 0 dc 0.405000
Rpre_right pre_right n_right 100e6
Rbl_right n_right n_right_mid 50.000000
Cbl_right n_right_mid 0 2.000000e-13
Rseg_right n_right_mid bl_right 0.1
Ccouple0 bl_left bl_sense 2.000000e-14
Ccouple1 bl_sense bl_right 2.000000e-14
Vpref pref 0 dc 0.405000
Rpref pref blb 100e6
Rblb blb blb_int 50.000000
Cblb blb_int 0 2.000000e-13
Rseg_b blb_int blb_sense 0.1
Vwl wl 0 PWL(0 0 1.900n 0 2.000n 0.810000 20.000n 0.810000 20.100n 0 30.000n 0)
Vaggr aggr_drv 0 PWL(0 0 2.500n 0 2.600n 0.202500 20.000n 0.202500 20.100n 0 30.000n 0)
Raggr aggr_drv bl_left 50
Vpl plate 0 dc 0.405000
Vs s 0 0
Mn1 bl_sense wl cell b nfet l=2.400e-08 nfin=1
Ccell cell plate 2.000000e-14
.ic v(bl_sense)=0.405000 v(blb_sense)=0.405000 v(cell)=0
.tran 0.05n 30.0n
.print tran v(bl_sense) v(blb_sense) v(bl_left) v(bl_right)
.measure tran dv_5ns FIND par('v(bl_sense)-v(blb_sense)') AT=5.0n
.measure tran dv_8ns FIND par('v(bl_sense)-v(blb_sense)') AT=8.0n
.measure tran dv_10ns FIND par('v(bl_sense)-v(blb_sense)') AT=10.0n
.measure tran dv_12ns FIND par('v(bl_sense)-v(blb_sense)') AT=12.0n
.measure tran dv_15ns FIND par('v(bl_sense)-v(blb_sense)') AT=15.0n
.end
