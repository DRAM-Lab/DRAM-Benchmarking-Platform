* Read column Ccell=15.0fF VBL_pre=0.383V
* Model: BCAT_125 | Corner: ss
.option gmin=1e-20 post=2 measdgt=8
.temp 27.0
.include 'models/OpenDRAMmodelV1/models/access_tx/BCAT_125.inc'

* Differential read column with lumped BL RC
* High-Z precharge (pre -> BL through 100 MΩ); signal at bl_sense / blb_sense
Vpre pre 0 dc 0.382500
Rpre pre bl 100e6
Vpref pref 0 dc 0.382500
Rpref pref blb 100e6
Rbl bl bl_int 71.428571
Cbl bl_int 0 1.400000e-13
Rblb blb blb_int 71.428571
Cblb blb_int 0 1.400000e-13
Rseg bl_int bl_sense 0.1
Rseg_b blb_int blb_sense 0.1
Vwl wl 0 PWL(0 0 1.900n 0 2.000n 0.765000 20.000n 0.765000 20.100n 0 30.000n 0)
Vpl plate 0 dc 0.382500
Vb b 0 0
Vs s 0 0
Mn1 bl_sense wl cell b nfet l=1.200e-07 nfin=1
Ccell cell plate 1.500000e-14
.ic v(bl)=0.382500 v(blb)=0.382500 v(bl_sense)=0.382500 v(blb_sense)=0.382500 v(cell)=0
.tran 0.05n 30.0n
.print tran v(bl_sense) v(blb_sense) v(cell) v(wl)
.measure tran dv_5ns FIND par('v(bl_sense)-v(blb_sense)') AT=5.0n
.measure tran dv_8ns FIND par('v(bl_sense)-v(blb_sense)') AT=8.0n
.measure tran dv_10ns FIND par('v(bl_sense)-v(blb_sense)') AT=10.0n
.measure tran dv_12ns FIND par('v(bl_sense)-v(blb_sense)') AT=12.0n
.measure tran dv_15ns FIND par('v(bl_sense)-v(blb_sense)') AT=15.0n
.end
