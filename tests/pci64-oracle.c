/* Host harness for unmodified functions extracted from pinned edk2 sources.
 * Only platform services are stubbed: fw_cfg, E820, a fresh GCD MMIO aperture,
 * and linked lists. No VM/firmware is booted and no allocator is reimplemented.
 */
#include <assert.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define IN
#define OUT
#define EFIAPI
#define STATIC static
#define VOID void
#define TRUE 1
#define FALSE 0
#define DEBUG(x)
#define ASSERT(x) assert(x)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define ALIGN_VALUE(a,b) (((a)+(b)-1)&~((b)-1))
#define LShiftU64(a,b) ((uint64_t)(a) << (b))
#define RShiftU64(a,b) ((uint64_t)(a) >> (b))
#define MAX_UINT64 UINT64_MAX
#define BASE_4GB (UINT64_C(1)<<32)
#define SIZE_1GB (UINT64_C(1)<<30)
#define EFI_SUCCESS 0
#define EFI_UNSUPPORTED 1
#define EFI_NOT_FOUND 2
#define EFI_ERROR(x) ((x)!=0)
#define BOOT_ON_S3_RESUME 1
#define EfiAcpiAddressRangeMemory 1
#define EfiGcdAllocateAddress 0
#define EfiGcdMemoryTypeMemoryMappedIo 0
#define EfiGcdIoTypeIo 0
#define PciBarTypeIo16 0
#define PciResUsageTypical 0
#define PciResUsagePadding 1
typedef uint64_t UINT64;
typedef uint32_t UINT32;
typedef size_t UINTN;
typedef int BOOLEAN, EFI_STATUS, FIRMWARE_CONFIG_ITEM;
typedef struct {
  UINT64 FirstNonAddress, PcdPciMmio64Base, PcdPciMmio64Size;
  BOOLEAN PcdPciMmio64Override;
  unsigned BootMode, PhysMemAddressWidth;
} EFI_HOB_PLATFORM_INFO;
typedef struct { UINT64 BaseAddr, Length; unsigned Type; } EFI_E820_ENTRY64;
static UINT64 high_ram, aperture_base, aperture_end;
static unsigned allocations;
static UINT64 GetPowerOfTwo64(UINT64 v) { return UINT64_C(1) << (63-__builtin_clzll(v)); }
static EFI_STATUS PlatformScanE820(void (*cb)(EFI_E820_ENTRY64 *, EFI_HOB_PLATFORM_INFO *), EFI_HOB_PLATFORM_INFO *h) {
  EFI_E820_ENTRY64 e = {BASE_4GB, high_ram, EfiAcpiAddressRangeMemory};
  if (high_ram) cb(&e,h);
  return EFI_SUCCESS;
}
static void PlatformReservationConflictCB(EFI_E820_ENTRY64 *e, EFI_HOB_PLATFORM_INFO *h) { (void)e; (void)h; abort(); }
static UINT64 PlatformGetSystemMemorySizeAbove4gb(void) { return high_ram; }
static EFI_STATUS QemuFwCfgParseUint32(const char *name, BOOLEAN hex, UINT32 *out) {
  assert(!hex && !strcmp(name,"opt/ovmf/X-PciMmio64Mb")); *out=32768; return EFI_SUCCESS;
}
static EFI_STATUS QemuFwCfgFindFile(const char *name, FIRMWARE_CONFIG_ITEM *item, UINTN *size) {
  assert(!strcmp(name,"etc/reserved-memory-end")); (void)item; (void)size; return EFI_NOT_FOUND;
}
static void QemuFwCfgSelectItem(FIRMWARE_CONFIG_ITEM item) { (void)item; abort(); }
static void QemuFwCfgReadBytes(UINTN size, void *out) { (void)size; (void)out; abort(); }
typedef struct list { struct list *ForwardLink, *BackLink; } LIST_ENTRY;
typedef struct {
  LIST_ENTRY Link, ChildList;
  UINT64 Length, Alignment, Offset;
  unsigned ResType, ResourceUsage;
} PCI_RESOURCE_NODE;
#define RESOURCE_NODE_FROM_LINK(p) ((PCI_RESOURCE_NODE *)((char *)(p)-offsetof(PCI_RESOURCE_NODE,Link)))
static LIST_ENTRY *GetFirstNode(LIST_ENTRY *h) { return h->ForwardLink; }
static LIST_ENTRY *GetNextNode(LIST_ENTRY *h, LIST_ENTRY *p) { (void)h; return p->ForwardLink; }
static BOOLEAN IsNull(LIST_ENTRY *h, LIST_ENTRY *p) { return h==p; }
static BOOLEAN IsListEmpty(LIST_ENTRY *h) { return h->ForwardLink==h; }
static void InitializeListHead(LIST_ENTRY *h) { h->ForwardLink=h->BackLink=h; }
static void InsertHeadList(LIST_ENTRY *h, LIST_ENTRY *p) {
  p->ForwardLink=h->ForwardLink; p->BackLink=h; h->ForwardLink->BackLink=p; h->ForwardLink=p;
}
static void RemoveEntryList(LIST_ENTRY *p) { p->BackLink->ForwardLink=p->ForwardLink; p->ForwardLink->BackLink=p->BackLink; }
static void SwapListEntries(LIST_ENTRY *a, LIST_ENTRY *b) {
  /* InsertResourceNode only swaps adjacent entries. */
  assert(a->ForwardLink==b); RemoveEntryList(a); InsertHeadList(b,a);
}
static void CalculateApertureIo16(PCI_RESOURCE_NODE *p) { (void)p; abort(); }
static EFI_STATUS AllocateSpace(unsigned type, unsigned memory, UINTN bits, UINT64 size, UINT64 *base, void *image, void *device) {
  (void)type; (void)memory; (void)image; (void)device;
  assert(!allocations++ && *base >= aperture_base && *base+size-1 <= aperture_end);
  assert(!(*base & ((UINT64_C(1)<<bits)-1))); return EFI_SUCCESS;
}
static void *gImageHandle;
static struct {
  EFI_STATUS (*AllocateMemorySpace)(unsigned,unsigned,UINTN,UINT64,UINT64 *,void *,void *);
  EFI_STATUS (*AllocateIoSpace)(unsigned,unsigned,UINTN,UINT64,UINT64 *,void *,void *);
} services = {AllocateSpace,AllocateSpace}, *gDS=&services;

#include "pci64-upstream.inc"

int main(int argc, char **argv) {
  assert(argc==3);
  UINT64 memory=strtoull(argv[1],NULL,10);
  high_ram=memory<2816 ? 0 : (memory-2048)<<20;
  EFI_HOB_PLATFORM_INFO h={.PcdPciMmio64Size=UINT64_C(32)<<30, .PhysMemAddressWidth=atoi(argv[2])};
  PlatformGetFirstNonAddress(&h);
  PlatformDynamicMmioWindow(&h);
  assert(h.PcdPciMmio64Override);
  aperture_base=h.PcdPciMmio64Base; aperture_end=h.FirstNonAddress-1;
  assert(h.FirstNonAddress <= (UINT64_C(1)<<h.PhysMemAddressWidth));
  PCI_RESOURCE_NODE pmem={.Alignment=0xfffff,.ResType=1}, mem=pmem, bars[4]={0};
  InitializeListHead(&pmem.ChildList); InitializeListHead(&mem.ChildList);
  for (unsigned i=0;i<4;i++) {
    bars[i].Length=0x4000; bars[i].Alignment=0x3fff; bars[i].ResType=1;
    InsertResourceNode(&pmem,&bars[i]);
  }
  MergeResourceTree(&mem,&pmem,FALSE);
  CalculateResourceAperture(&mem);
  UINTN bits=__builtin_ctzll(mem.Alignment+1);
  UINT64 base=AllocateResource(TRUE,mem.Length,bits,aperture_base,aperture_end);
  assert(base==aperture_base && mem.Length==0x100000);
  printf("%"PRIu64" %"PRIu64,aperture_base,aperture_end);
  for (unsigned i=0;i<4;i++) printf(" %"PRIu64,base+bars[i].Offset);
  puts("");
}
