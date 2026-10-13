fnid=$(date +%Y%m%d_%H%M%S)
finalfn=$(realpath ./backups/capture_$fnid.tar.zst)
tmpfn=$(mktemp -u -p backups --suffix=.tar)
tar -C out/ -vcf "$tmpfn" .
zstd -9 -T0 --rm "$tmpfn" -o "$finalfn"
