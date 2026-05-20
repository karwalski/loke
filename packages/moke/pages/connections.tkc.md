# connections.tk — API Connection Configuration

Handler for the "Connect to API" page (MK9.1).

## Module
`page.moke.connections`

## Routes
- `GET /connections` — renders the connections form UI

## Template
`templates/connections.tkt` — extends `base.tkt`

## Features (MK9.1)
- Connection name, URL, HTTP method selector
- Auth type selector (None / API Key / Bearer Token / Basic Auth / OAuth 2.0)
- Key-value editors for headers and query parameters
- JSON request body editor (POST/PUT only)
- Test Connection via loke proxy (`/api/proxy`)
- Save/load connections from localStorage (`moke_api_connections`)
- Placeholder sections for MK9.2–MK9.10

## Related Stories
- MK9.2: REST/JSON parser
- MK9.3: GraphQL editor
- MK9.4: OpenAPI discovery
- MK9.5: Auth configuration details
- MK9.6: data.gov.au browser
- MK9.8: Connection manager
- MK9.9: Cache status
- MK9.10: Rate limit status
