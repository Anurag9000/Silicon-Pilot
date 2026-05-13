# Exhaustive STM32 Ingestion Part 2
# Covers G0, G4, L0, L1, L4, L5, U5, WB, WL

def get_more_parts(p_func):
    PARTS = []
    # ══ STM32G0 — Cortex-M0+, 64 MHz ════════════════════════════════════════════
    for mpn,flash,sram,pkg,pins,uart,spi,i2c,adc,dac,gpio,cost in [
     ("STM32G030F6P6",32,8,"TSSOP",20,2,2,2,11,0,18,0.55),
     ("STM32G030J6M6",32,8,"SOIC",8,2,2,2,6,0,6,0.50),
     ("STM32G031C8T6",64,8,"LQFP",48,2,2,2,14,0,44,0.75),
     ("STM32G031G8U6",64,8,"UFQFPN",28,2,2,2,11,0,26,0.70),
     ("STM32G070CBT6",128,36,"LQFP",48,4,2,2,14,0,44,1.10),
     ("STM32G070RBT6",128,36,"LQFP",64,4,2,2,16,0,60,1.25),
     ("STM32G071CBT6",128,36,"LQFP",48,4,2,2,14,2,44,1.40),
     ("STM32G071RBT6",128,36,"LQFP",64,4,2,2,16,2,60,1.55),
     ("STM32G0B1RET6",512,144,"LQFP",64,6,3,3,16,2,60,2.10),
     ("STM32G0B1VET6",512,144,"LQFP",100,6,3,3,16,2,94,2.40),
    ]:
        PARTS.append(p_func(mpn,"STM32G0",pkg,pins,flash,sram,"Cortex-M0+",64,uart=uart,spi=spi,i2c=i2c,adc=adc,dac=dac,timers=9,pwm=14,gpio=gpio,dma=7,vmin=1.7,vmax=3.6,cost=cost))

    # ══ STM32G4 — Cortex-M4F, 170 MHz Mixed Signal ══════════════════════════════
    for mpn,flash,sram,pkg,pins,can,uart,spi,i2c,adc,dac,gpio,cost in [
     ("STM32G431C6T6",32,22,"LQFP",48,1,3,3,3,16,4,38,2.20),
     ("STM32G431C8T6",64,22,"LQFP",48,1,3,3,3,16,4,38,2.40),
     ("STM32G431CBT6",128,32,"LQFP",48,1,4,3,3,16,4,38,2.70),
     ("STM32G431RBT6",128,32,"LQFP",64,1,4,3,3,21,4,52,2.85),
     ("STM32G474RET6",512,128,"LQFP",64,3,5,4,4,26,7,52,4.50),
     ("STM32G474VET6",512,128,"LQFP",100,3,5,4,4,42,7,86,4.90),
     ("STM32G484QET6",512,128,"LQFP",144,3,5,4,4,42,7,114,5.50), # Has crypto
    ]:
        crypto = 1 if "G48" in mpn else 0
        PARTS.append(p_func(mpn,"STM32G4",pkg,pins,flash,sram,"Cortex-M4F",170,can=can,canfd=can,uart=uart,spi=spi,i2c=i2c,adc=adc,dac=dac,timers=14,pwm=24,fpu=1,dsp=1,crypto=crypto,gpio=gpio,dma=16,opamp=6,comp=7,vmin=1.71,vmax=3.6,cost=cost))

    # ══ STM32L4 & L4+ — Cortex-M4F, Ultra-low power ════════════════════════════
    for mpn,flash,sram,pkg,pins,mhz,can,usbfs,uart,spi,i2c,adc,dac,gpio,cost in [
     ("STM32L432KBU6",128,64,"UFQFPN",32,80,1,1,2,2,2,10,2,26,2.30),
     ("STM32L433CCT6",256,64,"LQFP",48,80,1,1,3,2,2,10,2,38,2.90),
     ("STM32L452RET6",512,160,"LQFP",64,80,1,1,4,3,3,16,2,52,3.50),
     ("STM32L476JGY6",1024,128,"WLCSP",72,80,1,1,5,3,3,16,2,57,4.80),
     ("STM32L476RGT6",1024,128,"LQFP",64,80,1,1,5,3,3,16,2,51,4.50),
     ("STM32L476VGT6",1024,128,"LQFP",100,80,1,1,5,3,3,16,2,82,4.90),
     ("STM32L496ZGT6",1024,320,"LQFP",144,80,2,1,6,3,4,24,2,115,5.60),
     ("STM32L4R5ZIT6",2048,640,"LQFP",144,120,2,1,6,3,4,24,2,115,8.50), # L4+
     ("STM32L4S9AII6",2048,640,"UFBGA",169,120,2,1,6,3,4,24,2,131,9.80), # L4+ with graphics
    ]:
        PARTS.append(p_func(mpn,"STM32L4",pkg,pins,flash,sram,"Cortex-M4F",mhz,can=can,usbfs=usbfs,uart=uart,spi=spi,i2c=i2c,adc=adc,dac=dac,timers=11,pwm=18,fpu=1,dsp=1,gpio=gpio,dma=14,vmin=1.71,vmax=3.6,cost=cost))

    # ══ STM32U5 — Cortex-M33, Advanced Ultra-low power ═════════════════════════
    for mpn,flash,sram,pkg,pins,uart,spi,i2c,adc,dac,gpio,cost in [
     ("STM32U575CGT6",1024,786,"LQFP",48,5,3,4,14,2,38,5.10),
     ("STM32U575RIT6",2048,786,"LQFP",64,5,3,4,16,2,51,5.80),
     ("STM32U585AII6",2048,786,"UFBGA",169,5,3,4,20,2,131,7.50),
     ("STM32U599NJH6",4096,2500,"TFBGA",216,6,4,5,24,2,156,12.50),
    ]:
        PARTS.append(p_func(mpn,"STM32U5",pkg,pins,flash,sram,"Cortex-M33",160,canfd=2,usbfs=1,usbhs=1,uart=uart,spi=spi,i2c=i2c,adc=adc,dac=dac,timers=17,pwm=24,fpu=1,dsp=1,crypto=1,gpio=gpio,dma=16,vmin=1.71,vmax=3.6,cost=cost))

    # ══ STM32WB — Wireless Cortex-M4 + Cortex-M0+ (BLE/Zigbee/Thread) ═════════
    for mpn,flash,sram,pkg,pins,gpio,cost in [
     ("STM32WB55CGU6",1024,256,"UFQFPN",48,37,4.50),
     ("STM32WB55RGV6",1024,256,"VQFN",68,51,4.90),
     ("STM32WB15CCU6",320,48,"UFQFPN",48,37,2.80),
    ]:
        PARTS.append(p_func(mpn,"STM32WB",pkg,pins,flash,sram,"Cortex-M4+M0+",64,usbfs=1,uart=2,spi=2,i2c=2,adc=16,dac=0,timers=7,pwm=10,fpu=1,dsp=1,wireless=1,gpio=gpio,dma=7,vmin=1.71,vmax=3.6,cost=cost))

    return PARTS
