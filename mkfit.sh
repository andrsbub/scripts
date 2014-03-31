#!/bin/bash
LOADADDR=0x408000
if [ "$1" == "--load" -a ! -z "$2" ]; then
  LOADADDR=$2
  echo "Using load-addr ${LOADADDR}"
  shift 2
fi
DTB=$1
if [ -z "$DTB" ]; then
  DTB=axm55xx
fi
if [ ! -r ./arch/arm/boot/dts/${DTB}.dts ]; then
  echo "${DTB}.dts: Not found"
  exit 1
else
  echo "Building DTB"
  make ${DTB}.dtb
fi
[ $? -eq 0 ] || exit $?

if [ ! -r arch/arm/boot/Image ];then
  echo "No Image found"
  exit 1
fi

cat arch/arm/boot/Image | gzip -c > arch/arm/boot/vmlinux.bin.gz

TMPFILE=kernel-fdt-${USER}.$$
cat >$TMPFILE <<-EOF
/dts-v1/;

/ {
	description = "Simple image with single Linux kernel and FDT blob";
	#address-cells = <1>;

	images {
		kernel@1 {
			description = "Linux kernel";
			data = /incbin/("./arch/arm/boot/vmlinux.bin.gz");
			type = "kernel";
			arch = "arm";
			os = "linux";
			compression = "gzip";
			load = <${LOADADDR}>;
			entry = <${LOADADDR}>;
			hash@1 {
				algo = "crc32";
			};
			hash@2 {
				algo = "sha1";
			};
		};
		fdt@1 {
			description = "Flattened Device Tree blob";
			data = /incbin/("./arch/arm/boot/dts/${DTB}.dtb");
			type = "flat_dt";
			arch = "arm";
			compression = "none";
			hash@1 {
				algo = "crc32";
			};
			hash@2 {
				algo = "sha1";
			};
		};
	};

	configurations {
		default = "conf@1";
		conf@1 {
			description = "Boot Linux kernel with FDT blob";
			kernel = "kernel@1";
			fdt = "fdt@1";
		};
	};
};
EOF

mkimage -f $TMPFILE linux.fit
rm -f $TMPFILE
