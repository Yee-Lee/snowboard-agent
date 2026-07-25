/*****************************************************************************
* | File      	:   DEV_Config.c
* | Author      :   Waveshare team
* | Function    :   Hardware underlying interface
* | Info        :
*----------------
* |	This version:   V2.0
* | Date        :   2019-07-08
* | Info        :   Basic version
*
******************************************************************************/
#include "DEV_Config.h"
#include <unistd.h>

#if USE_DEV_LIB
int GPIO_Handle;
int SPI_Handle;
#endif

void DEV_SetBacklight(UWORD Value)
{
#ifdef USE_BCM2835_LIB
    bcm2835_pwm_set_data(0,Value);
#elif USE_WIRINGPI_LIB
    pwmWrite(LCD_BL,Value);
#elif USE_DEV_LIB
    // 簡單的開關：如果有亮度就拉高，為 0 就拉低
    if (Value > 0) {
        lgGpioWrite(GPIO_Handle, LCD_BL, 1);
    } else {
        lgGpioWrite(GPIO_Handle, LCD_BL, 0);
    }
#endif
}

/*****************************************
                GPIO
*****************************************/
void DEV_Digital_Write(UWORD Pin, UBYTE Value)
{
#ifdef USE_BCM2835_LIB
    bcm2835_gpio_write(Pin, Value);
#elif USE_WIRINGPI_LIB
    digitalWrite(Pin, Value);
#elif USE_DEV_LIB
    lgGpioWrite(GPIO_Handle, Pin, Value);
#endif
}

UBYTE DEV_Digital_Read(UWORD Pin)
{
    UBYTE Read_value = 0;
#ifdef USE_BCM2835_LIB
    Read_value = bcm2835_gpio_lev(Pin);
#elif USE_WIRINGPI_LIB
    Read_value = digitalRead(Pin);
#elif USE_DEV_LIB
    Read_value = lgGpioRead(GPIO_Handle, Pin);
#endif
    return Read_value;
}

void DEV_GPIO_Mode(UWORD Pin, UWORD Mode)
{
#ifdef USE_BCM2835_LIB  
    if(Mode == 0 || Mode == BCM2835_GPIO_FSEL_INPT){
        bcm2835_gpio_fsel(Pin, BCM2835_GPIO_FSEL_INPT);
    }else {
        bcm2835_gpio_fsel(Pin, BCM2835_GPIO_FSEL_OUTP);
    }
#elif USE_WIRINGPI_LIB
    if(Mode == 0 || Mode == INPUT){
        pinMode(Pin, INPUT);
        pullUpDnControl(Pin, PUD_UP);
    }else{ 
        pinMode(Pin, OUTPUT);
    }
#elif USE_DEV_LIB
    if(Mode == 0 || Mode == LG_SET_INPUT){
        lgGpioClaimInput(GPIO_Handle, LFLAGS, Pin);
    }else{
        lgGpioClaimOutput(GPIO_Handle, LFLAGS, Pin, LG_LOW);
    }
#endif   
}

/**
 * delay x ms
**/
void DEV_Delay_ms(UDOUBLE xms)
{
#ifdef USE_BCM2835_LIB
    bcm2835_delay(xms);
#elif USE_WIRINGPI_LIB
    delay(xms);
#elif USE_DEV_LIB
    lguSleep(xms / 1000.0);
#endif
}

static void DEV_GPIO_Init(void)
{
    DEV_GPIO_Mode(LCD_RST, 1);
    DEV_GPIO_Mode(LCD_DC, 1);
    DEV_GPIO_Mode(LCD_BL, 1);
    
    DEV_GPIO_Mode(KEY_UP_PIN, 0);
    DEV_GPIO_Mode(KEY_DOWN_PIN, 0);
    DEV_GPIO_Mode(KEY_LEFT_PIN, 0);
    DEV_GPIO_Mode(KEY_RIGHT_PIN, 0);
    DEV_GPIO_Mode(KEY_PRESS_PIN, 0);
    DEV_GPIO_Mode(KEY1_PIN, 0);
    DEV_GPIO_Mode(KEY2_PIN, 0);
    DEV_GPIO_Mode(KEY3_PIN, 0);

    LCD_BL_1; // 初始化時拉高背光
}

/******************************************************************************
function:	Module Initialize, the library and initialize the pins, SPI protocol
parameter:
Info:
******************************************************************************/
UBYTE DEV_ModuleInit(void)
{
#ifdef USE_BCM2835_LIB
    if(!bcm2835_init()) {
        printf("bcm2835 init failed  !!! \r\n");
        return 1;
    } else {
        printf("bcm2835 init success !!! \r\n");
    }
    DEV_GPIO_Init();
    bcm2835_spi_begin();                                         //Start spi interface, set spi pin for the reuse function
    bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST);     //High first transmission
    bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);                  //spi mode 0
    bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_32);  //Frequency
    bcm2835_spi_chipSelect(BCM2835_SPI_CS0);                     //set CE0
    bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);     //enable cs0
	
    bcm2835_gpio_fsel(LCD_BL, BCM2835_GPIO_FSEL_ALT5);
    bcm2835_pwm_set_clock(BCM2835_PWM_CLOCK_DIVIDER_16);
    bcm2835_pwm_set_mode(0, 1, 1);
    bcm2835_pwm_set_range(0,1024);
    bcm2835_pwm_set_data(0,512);
	
#elif USE_WIRINGPI_LIB  
    if(wiringPiSetupGpio() < 0) { //use BCM2835 Pin number table
        printf("set wiringPi lib failed	!!! \r\n");
        return 1;
    } else {
        printf("set wiringPi lib success  !!! \r\n");
    }
    DEV_GPIO_Init();
    wiringPiSPISetup(0,40000000);
    pinMode (LCD_BL, PWM_OUTPUT);
    pwmWrite(LCD_BL,512);
#elif USE_DEV_LIB
    char buffer[NUM_MAXBUF];
    FILE *fp1;

    fp1 = popen("cat /proc/cpuinfo | grep 'Raspberry Pi 5'", "r");
    if (fp1 == NULL) {
        printf("It is not possible to determine the model of the Raspberry PI\n");
        return -1;
    }

    if(fgets(buffer, sizeof(buffer), fp1) != NULL)  
    {
        GPIO_Handle = lgGpiochipOpen(4);
        if (GPIO_Handle < 0)
        {
            printf("gpiochip4 Export Failed\n");
            return -1;
        }
    }
    else
    {
        GPIO_Handle = lgGpiochipOpen(0);
        if (GPIO_Handle < 0)
        {
            printf("gpiochip0 Export Failed\n");
            return -1;
        }
    }
    pclose(fp1);

    DEV_GPIO_Init();
    
    // 開啟 SPI0 晶片通道 0，設定頻率為 20MHz (20000000)
    SPI_Handle = lgSpiOpen(0, 0, 20000000, 0);
    if (SPI_Handle < 0) {
        printf("lgSpiOpen Failed\n");
        return -1;
    }
#endif
    return 0;
}

void DEV_SPI_WriteByte(uint8_t Value)
{
#ifdef USE_BCM2835_LIB
    bcm2835_spi_transfer(Value);
#elif USE_WIRINGPI_LIB
    wiringPiSPIDataRW(0,&Value,1);
#elif USE_DEV_LIB
    lgSpiWrite(SPI_Handle, (char*)&Value, 1);
#endif
}

void DEV_SPI_Write_nByte(uint8_t *pData, uint32_t Len)
{
#ifdef USE_BCM2835_LIB
    uint8_t rData[Len];
    bcm2835_spi_transfernb((char *)pData,(char *)rData,Len);
#elif USE_WIRINGPI_LIB
    wiringPiSPIDataRW(0, (unsigned char *)pData, Len);
#elif USE_DEV_LIB
    lgSpiWrite(SPI_Handle, (char*)pData, Len);
#endif
}

/******************************************************************************
function:	Module exits, closes SPI and BCM2835 library
parameter:
Info:
******************************************************************************/
void DEV_ModuleExit(void)
{
#ifdef USE_BCM2835_LIB
    bcm2835_spi_end();
    bcm2835_close();
#elif USE_WIRINGPI_LIB

#elif USE_DEV_LIB
    lgSpiClose(SPI_Handle);
    lgGpiochipClose(GPIO_Handle);
#endif
}
