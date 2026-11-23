arg="${1:-now}"
d=$(date -d "$arg" +%F)
output="${2:-broadcast_list_$d.json}"
curl -fsSL "https://apigateway.vtvcab.vn/mycab/api/v2/landing-page/broadcast_list?date=$d" -o "$output"
