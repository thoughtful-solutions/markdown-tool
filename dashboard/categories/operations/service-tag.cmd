@echo off
rem provide a list of roles by service
rem this comes from the gherkin implementation approach
jq -r ".scenarios[0].steps[3].stdout" service-tag.stdout | jq -r ".[] | \"Service: \(.service)\", (if (.roles | length) > 0 then .roles[] | \"  - \(.)\" else \"  - (No roles defined)\" end)"
