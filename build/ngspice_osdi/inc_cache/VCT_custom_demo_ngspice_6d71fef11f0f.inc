* ngspice OSDI compatibility patch for VCT_custom_demo
* HSPICE level 72 -> bsimcmg_va (experimental)
* Source: /home/yongfu/proj/dram-lab/projects/DRAM-Benchmarking-Platform/models/samples/custom_vct_demo/VCT_custom_demo.inc
** OpenDRAMBench sample card — VCT_custom_demo
** Derived from bundled VCT_125; edit parameters below to trial your own access device.
**
** Platform parser reads from this file (see models/samples/README.md):
**   - Header: Nominal VDD line with a numeric value (example below)
**   - Parameters: bulkmod, l, nfin, fpitch, vsat (BSIM-CMG level 72)
**
** Filename stem (VCT_custom_demo) is the model ID for --model.
** Architecture is inferred from the ID prefix: BCAT_, VCT_, or 3D_gaa_.
**
** PTM-MG HSPICE Model Card for 20nm LSTP NFET 
** Nominal VDD=0.9V

.model nfet bsimcmg_va
+ TYPE = 1 
+ BULKMOD = 0 
+                
************************************************************
*                         general                          *
************************************************************
*========================= FLAGS ==========================*
+          BULKMOD = 0               IGCMOD  = 0               IGBMOD  = 0             
+GIDLMOD = 0               IIMOD   = 0               GEOMOD  = 1               RDSMOD  = 1             
+RGATEMOD= 0               RGEOMOD = 1               SHMOD   = 0               NQSMOD  = 0             
+               CGEOMOD = 2                              TNOM    = 300.15        
*======================== PROCESS =========================*
+EOT     = 5e-009        EOTBOX  = 1.4e-007        TFIN    = 1.75e-008        TOXP    = 5e-009      
+NBODY   = 5e+023          PHIG    = 4.7968          EPSROX  = 3.9             EPSRSUB = 11.9          
+EASUB   = 4.05            NI0SUB  = 1.1e+016        BG0SUB  = 1.12            NC0SUB  = 2.86e+025     
+NSD     = 3e+026          NGATE   = 0               NFIN    = 1               D       = 4e-008        
+               L       = 2.4e-008      
*========================== w/L ===========================*
+XL      = 0               LINT    = -1.5e-009       LL      = 0               LLN     = 1             
+LLC     = 0               DLC     = 0               DLBIN   = 0               HFIN    = 5e-009      
+FECH    = 1               DELTAW  = 0               DELTAWCV= 0               FECHCV  = 1             
+HEPI    = 1e-008        
*======================== GEOMETRY ========================*
+TSILI   = 1e-008          RHOC    = 4e-012        CRATIO  = 0.5             DELTAPRSD= 0             
+SDTERM  = 0                         EPSRSP  = 3.9             TGATE   = 1e-008        
+TMASK   = 0               ASILIEND= 0               ARSDEND = 0               PRSDEND = 0             
+NSDE    = 3e+025          RGEOA   = 1               RGEOB   = 0               RGEOC   = 0             
+RGEOD   = 0               RGEOE   = 0               CGEOA   = 1               CGEOB   = 0             
+CGEOC   = 0               CGEOD   = 0               CGEOE   = 1             
*===================== MODEL_SELECTOR =====================*
************************************************************
*                            dc                            *
************************************************************
+CIT     = 1.3e-003      
*========================== VTH ===========================*
+CDSC    = 0.01695         CDSCD   = 0.007           DVT0    = 0.01            DVT1    = 0.69          
+PHIN    = 0.05            ETA0    = 0.6656          DSUB    = 0.9             K1RSCE  = 0             
+LPE0    = 5e-009          DVTSHIFT= 0               QMFACTOR= 0                            
+QMTCENCV= 0               ETAQM   = 0.54            QM0     = 0.001143        PQM     = 0.66          
+QM0ACC  = 0.001           PQMACC  = 0.66            DELVFBACC= 0               U0      = 0.028         
*======================== MOBILITY ========================*
+ETAMOB  = 2               UP      = 0               LPA     = 1               UA      = 0           
+AUA     = 0               BUA     = 1e-007          EU      = 1.8             UD      = 0.5             
+AUD     = 0               BUD     = 5e-008          UCS     = 0               RDSWMIN = 0             
*======================= RESISTANCE =======================*
+RDSW    = 100             ARDSW   = 0               BRDSW   = 1e-007                       
+WR      = 1               RSWMIN  = 0               RSW     = 74               ARSW    = 0             
+BRSW    = 1e-007          RDWMIN  = 0               RDW     = 74               ARDW    = 0             
+BRDW    = 1e-007          RGFIN   = 0.001           RGEXT   = 0               RSHS    = 0             
+VSAT    = 28720         
*======================= SATURATION =======================*
+DELTAVSAT= 1               KSATIV  = 0.8             AVSAT   = 0               AVSAT1  = 0             
+BVSAT   = 1e-007          BVSAT1  = 1e-007          MEXP    = 3               AMEXP   = 0             
+BMEXP   = 1               PTWG    = 0               APTWG   = 0               BPTWG   = 1e-007        
*========================== ROUT ==========================*
+PCLM    = 0.2             PCLMCV  = 0.013           APCLM   = 0               BPCLM   = 1e-007        
+PCLMG   = 0                                                      
+PDIBL1  = 1.3             PDIBL2  = 0.0002          DROUT   = 1.06            PVAG    = 1             
+FPITCH  = 6e-008        
*====================== self-HEATING ======================*
+RTH0    = 0.01            CTH0    = 1e-005          WTH0    = 0             
************************************************************
*                         leakage                          *
************************************************************
+AIGBINV = 0.0111        
*========================== IGB ===========================*
+BIGBINV = 0.03            CIGBINV = 0.006           EIGBINV = 1.1             NIGBINV = 1.2             
+AIGBACC = 0.0149          BIGBACC = 0.000949        CIGBACC = 0.075           NIGBACC = 3             
+AIGC    = 0.0136        
*========================== IGC ===========================*
+BIGC    = 0.00171         CIGC    = 0.075                        
*======================== igs/IGD =========================*
+DLCIGS  = 0               DLCIGD  = 0               AIGS    = 0.0136          AIGD    = 0.0136        
+BIGS    = 0.00171         BIGD    = 0.00171         CIGS    = 0.075           CIGD    = 0.075         
+POXEDGE = 1               AGIDL   = 5.729e-012    
*======================= gidl/GISL ========================*
+AGISL   = 5.729e-012      BGIDL   = 3e+008          BGISL   = 3e+008          EGIDL   = 0.1           
+EGISL   = 0.1             ALPHA0  = 0             
*========================== ISUB ==========================*
+ALPHA1  = 0                              BETAII0 = 0               BETAII1 = 0             
+BETAII2 = 0.1             ESATII  = 10000000        LII     = 5e-010          SII0    = 0.5           
+SII1    = 0.1             SII2    = 0               SIID    = 0               BETA0   = 30            
+LINTIGEN= 0             
*================ generation/RECOMBINATION ================*
+NTGEN   = 1               AIGEN   = 0               BIGEN   = 0             
************************************************************
*                            rf                            *
************************************************************
+XRCRG1  = 12            
*==================== nonquasi-STATIC =====================*
+XRCRG2  = 1             
************************************************************
*                         junction                         *
************************************************************
*======================== CURRENT =========================*
+JSS     = 0.0001          JSD     = 0.0001          JSWS    = 0               JSWGS   = 0             
+NJS     = 1               NJD     = 1               IJTHSFWD= 0.1             IJTHDFWD= 0.1           
+IJTHSREV= 0.1             IJTHDREV= 0.1             BVS     = 10              BVD     = 10            
+XJBVS   = 1               XJBVD   = 1               CJS     = 0.0005        
*====================== CAPACITANCE =======================*
+CJD     = 0.0005          CJSWS   = 5e-010          CJSWGS  = 0               PBS     = 1             
+PBD     = 1               PBSWS   = 1               MJS     = 0.5             MJD     = 0.5           
+MJSWS2  = 0.33            MJSWD2  = 0.33            MJSWS   = 0.33            SJS     = 0             
+SJSWS   = 0               SJSWGS  = 0               MJS2    = 0.125           MJD2    = 0.125         
************************************************************
*                       capacitance                        *
************************************************************
*====================== CAPACITANCE =======================*
+CGSP    = 0               CGDP    = 0               CDSP    = 0               CFS     = 2.56e-011     
+CFD     = 2.65e-011       COVS    = 2.5e-011        COVD    = 2.5e-011        CGSL    = 0             
+CKAPPAS = 0.6             CGBO    = 0               CGBL    = 0             
************************************************************
*                       temperature                        *
************************************************************
+TBGASUB = 0.000702      
*======================== PROCESS =========================*
+TBGBSUB = 1108            KT1     = 0             
*========================== VTH ===========================*
+KT1L    = 0               UTE     = 0             
*======================== MOBILITY ========================*
+UTL     = -0.0015         UA1     = 0.001032        UD1     = 0               UCSTE   = -0.00478      
+AT      = -0.00156      
*========================== VSAT ==========================*
+PTWGT   = 0.004           TMEXP   = 0               PRT     = 0.001         
*======================== RESISTOR ========================*
+IIT     = -0.5          
*========================== ISUB ==========================*
+TII     = 0               TGIDL   = -0.0003       
*========================== GIDL ==========================*
+IGT     = 2.5           
*====================== GATECURRENT =======================*
*======================== JUNCTION ========================*
+TCJ     = 0               TCJSW   = 0               TCJSWG  = 0               TPB     = 0             
+TPBSW   = 0               TPBSWG  = 0               XTIS    = 3               XTID    = 3             
+XTSS    = 0.02            XTSSWS  = 0.02            XTSSWGS = 0.02            TNJTS   = 0             
+TNJTSSW = 0               TNJTSSWG= 0             
************************************************************
*                          noise                           *
************************************************************
+EF      = 1             
*========================== 1/F ===========================*
+LINTNOI = 0               EM      = 41000000        NOIA    = 6.25e+039       NOIB    = 3.125e+024    
+NOIC    = 87500000        NTNOI   = 1             
