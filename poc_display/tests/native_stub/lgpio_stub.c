#include "lgpio.h"

int lgGpiochipOpen(int gpioDev) { (void)gpioDev; return 1; }
int lgGpiochipClose(int handle) { (void)handle; return 0; }
int lgGpioClaimOutput(int handle, int lFlags, int gpio, int level)
{
    (void)handle; (void)lFlags; (void)gpio; (void)level; return 0;
}
int lgGpioClaimInput(int handle, int lFlags, int gpio)
{
    (void)handle; (void)lFlags; (void)gpio; return 0;
}
int lgGpioWrite(int handle, int gpio, int level)
{
    (void)handle; (void)gpio; (void)level; return 0;
}
int lgGpioRead(int handle, int gpio)
{
    (void)handle; (void)gpio; return 0;
}
int lgSpiOpen(int spiDev, int spiChan, int baud, int spiFlags)
{
    (void)spiChan; (void)baud; (void)spiFlags;
    return spiDev == 99 ? -1 : 2;
}
int lgSpiClose(int handle) { (void)handle; return 0; }
int lgSpiWrite(int handle, const char *txBuf, int count)
{
    (void)handle; (void)txBuf; return count;
}
void lguSleep(double seconds) { (void)seconds; }
