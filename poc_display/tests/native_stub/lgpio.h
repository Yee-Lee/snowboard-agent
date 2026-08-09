#ifndef POC_DISPLAY_TEST_LGPIO_H
#define POC_DISPLAY_TEST_LGPIO_H

int lgGpiochipOpen(int gpioDev);
int lgGpiochipClose(int handle);
int lgGpioClaimOutput(int handle, int lFlags, int gpio, int level);
int lgGpioClaimInput(int handle, int lFlags, int gpio);
int lgGpioWrite(int handle, int gpio, int level);
int lgGpioRead(int handle, int gpio);
int lgSpiOpen(int spiDev, int spiChan, int baud, int spiFlags);
int lgSpiClose(int handle);
int lgSpiWrite(int handle, const char *txBuf, int count);
void lguSleep(double seconds);

#endif
