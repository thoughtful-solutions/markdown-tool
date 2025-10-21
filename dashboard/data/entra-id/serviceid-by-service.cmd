jq -r ".services[] | \"\(.serviceId): \(.displayName)\"" entra.json
