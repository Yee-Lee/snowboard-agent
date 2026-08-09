#include "display.h"

int main(void)
{
    DisplayConfig config;
    DisplayInfo info = {0};
    DisplayHandle handle = DISPLAY_INVALID_HANDLE;
    DisplayStatus status = DISPLAY_OK;

    display_config_init(&config);
    (void)info;
    (void)handle;
    return status == DISPLAY_OK && display_abi_version() == DISPLAY_ABI_VERSION
        ? 0
        : 1;
}
