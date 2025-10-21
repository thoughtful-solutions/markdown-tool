jq ".services[] | select(.tags and (.tags | any(. == \"Finance\")))" entra.json
