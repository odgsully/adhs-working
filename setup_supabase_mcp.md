# Setting Up Supabase MCP Server

## Steps to Complete Setup:

### 1. Get Your Supabase Project Reference
- Go to your Supabase dashboard: https://supabase.com/dashboard
- Select your project
- Go to Settings → General
- Copy your "Reference ID" (looks like: `abcdefghijklmnop`)

### 2. Generate a Supabase Access Token
- Go to: https://supabase.com/dashboard/account/tokens
- Click "Generate New Token"
- Name it: "ADHS ETL MCP Server"
- Copy the token (you won't see it again!)

### 3. Configure the MCP Server

Run this command with your actual values:

```bash
claude mcp remove supabase
claude mcp add supabase npx -- -y @supabase/mcp-server-supabase --read-only --project-ref=YOUR_PROJECT_REF -e SUPABASE_ACCESS_TOKEN=YOUR_TOKEN
```

Replace:
- `YOUR_PROJECT_REF` with your project reference ID
- `YOUR_TOKEN` with your access token

### 4. Test the Connection

```bash
claude mcp list
```

You should see: `supabase: npx -y @supabase/mcp-server-supabase ... - ✓ Connected`

## Available Commands Once Connected

The Supabase MCP will provide tools like:
- Query your database
- Create/modify tables (if not in read-only mode)
- Manage database schema
- Execute SQL queries
- Manage database functions and triggers

## Security Notes

- We're using `--read-only` flag for safety
- This prevents accidental modifications to your data
- Remove `--read-only` if you need write access
- Always use with development/staging databases, not production

## Troubleshooting

If connection fails:
1. Verify your project reference ID is correct
2. Check your access token is valid
3. Ensure you have internet connectivity
4. Try regenerating the access token if needed