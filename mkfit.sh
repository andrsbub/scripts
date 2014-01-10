#!/bin/bash
DTB=$1
if [ -z "$DTB" ]; then
  DTB=axm55xx
fi
if [ ! -r ./arch/arm/boot/dts/${DTB}.dts ]; then
  echo "${DTB}.dts: Not found"
  exit 1
fi
./scripts/dtc/dtc -O dtb -R 32 -p 0x400 -o arch/arm/boot/current.dtb arch/arm/boot/dts/${DTB}.dts
[ $? -eq 0 ] || exit $?
cat arch/arm/boot/Image | gzip -c > arch/arm/boot/vmlinux.bin.gz
mkimage -f kernel_fdt.its linux.fit
