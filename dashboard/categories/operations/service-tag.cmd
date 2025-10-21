jq -r ".scenarios[0].steps[3].stdout" service-tag.log | jq -r ".[] | \"Service: \(.service)\", (if (.roles | length) > 0 then .roles[] | \"  - \(.)\" else \"  - (No roles defined)\" end)"
