/* Host oracle using the pinned upstream edk2 measurement filter. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#undef NULL
#include "MdeModulePkg/Universal/SmbiosMeasurementDxe/SmbiosMeasurementDxe.c"
VOID *EFIAPI CopyMem(VOID *Destination, CONST VOID *Source, UINTN Length) {return memcpy(Destination,Source,Length);}
VOID *EFIAPI SetMem(VOID *Buffer, UINTN Length, UINT8 Value) {return memset(Buffer,Value,Length);}
VOID *EFIAPI ZeroMem(VOID *Buffer, UINTN Length) {return memset(Buffer,0,Length);}
int main(void) {
 unsigned char buffer[65536]; size_t len=fread(buffer,1,sizeof(buffer),stdin);
 mMaxLen = 0xffff; FilterSmbiosTable(buffer,len);
 return fwrite(buffer,1,len,stdout)==len?0:1;
}
BOOLEAN EFIAPI DebugCodeEnabled(VOID) {return FALSE;}
