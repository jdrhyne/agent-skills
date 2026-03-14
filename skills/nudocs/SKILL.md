---
name: nudocs
description: Upload, edit, and export documents via Nudocs.ai. Use when creating shareable document links for collaborative editing, uploading markdown/docs to Nudocs for rich editing, or pulling back edited content. Triggers on "send to nudocs", "upload to nudocs", "edit in nudocs", "pull from nudocs", "get the nudocs link", "show my nudocs documents".
homepage: https://nudocs.ai
permissions:
  - exec: "Runs the Nudocs CLI for upload, list, link, pull, and delete operations."
  - file_write: "Creates or downloads local document files only for the user-requested Nudocs workflow."
  - credential_access: "Reads the Nudocs API key from the documented env var or local config path."
  - network: "Calls Nudocs.ai through the documented CLI and service endpoints."
metadata:
  {
    "openclaw":
      {
        "emoji": "📄",
        "requires":
          {
            "bins": ["nudocs"],
            "env": ["NUDOCS_API_KEY"],
            "config": ["~/.config/nudocs/api_key"],
          },
        "install":
          [
            {
              "id": "npm",
              "kind": "node",
              "package": "@nutrient-sdk/nudocs-cli",
              "repo": "https://github.com/PSPDFKit/nudocs-cli",
              "bins": ["nudocs"],
              "label": "Install Nudocs CLI (npm)",
            },
          ],
      },
  }
---

# Nudocs

Upload documents to Nudocs.ai for rich editing, get shareable links, and pull back the results.

## Setup

1. Install the CLI using the repo's declared install metadata or your preferred package manager before first use.

2. Get your API key from https://nudocs.ai (click "Integration" after signing in)

3. Configure the key:
```bash
# Option 1: Environment variable
export NUDOCS_API_KEY="nudocs_your_key_here"

# Option 2: Config file
mkdir -p ~/.config/nudocs
echo "nudocs_your_key_here" > ~/.config/nudocs/api_key
```

## Commands

```bash
nudocs upload <file>              # Upload and get edit link
nudocs list                       # List all documents
nudocs link [ulid]                # Get edit link (last upload if no ULID)
nudocs pull [ulid] [--format fmt] # Download document (default: docx)
nudocs delete <ulid>              # Delete a document
nudocs config                     # Show configuration
```

## Workflow

### Upload Flow
1. Create/write document content
2. Save as markdown (or other supported format)
3. Run: `nudocs upload <file>`
4. Share the returned edit link with user

### Pull Flow
1. User requests document back
2. Run: `nudocs pull [ulid] --format <fmt>`
3. Read and present the downloaded file

### Format Selection

| Scenario | Recommended Format |
|----------|-------------------|
| User edited with rich formatting | `docx` (default) |
| Simple text/code content | `md` |
| Final delivery/sharing | `pdf` |

See `formats.md` in this skill's `references` folder for full format support.

## Natural Language Triggers

Recognize these user intents:

**Upload/Send:**
- "send to nudocs"
- "upload to nudocs"  
- "open in nudocs"
- "edit this in nudocs"
- "let me edit this in nudocs"
- "put this in nudocs"

**Pull/Fetch:**
- "pull it back"
- "pull from nudocs"
- "get that doc"
- "fetch from nudocs"
- "download from nudocs"
- "grab the updated version"
- "what did I change"
- "get my edits"

**Link:**
- "get the nudocs link"
- "share link"
- "where's that doc"
- "nudocs url"

**List:**
- "show my nudocs"
- "list my documents"
- "what docs do I have"
- "my nudocs documents"

## Document Best Practices

Before uploading, ensure good structure:
- Clear heading hierarchy (H1 → H2 → H3)
- Consistent spacing
- Appropriate list formatting
- Concise paragraphs (3-5 sentences)

See `document-design.md` in this skill's `references` folder for templates and guidelines.

## Example Session

```
User: Write me a blog post about remote work and send it to Nudocs

Agent:
1. Writes blog-remote-work.md with proper structure
2. Runs: nudocs upload blog-remote-work.md
3. Returns: "Here's your Nudocs link: https://nudocs.ai/file/01ABC..."

User: *edits in Nudocs, adds formatting, images*
User: Pull that back

Agent:
1. Runs: nudocs pull --format docx
2. Reads the downloaded file
3. Returns: "Got your updated document! Here's what changed..."
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| "No API key found" | Missing credentials | Set NUDOCS_API_KEY or create config file |
| "DOCUMENT_LIMIT_REACHED" | Free tier limit (10 docs) | Delete old docs or upgrade to Pro |
| "Unauthorized" | Invalid API key | Regenerate key in Nudocs settings |
| "No ULID provided" | Missing document ID | Specify ULID or upload a doc first |

## Links

- CLI: https://github.com/PSPDFKit/nudocs-cli (`@nutrient-sdk/nudocs-cli` on npm)
- MCP integration repo: https://github.com/PSPDFKit/nudocs-mcp-server
- Nudocs: https://nudocs.ai

## Safety Boundaries

- Do not upload sensitive documents unless the user confirmed that third-party processing is acceptable.
- Do not print API keys, edit links meant to stay private, or document contents the user did not ask to expose.
- Do not delete documents from Nudocs without explicit confirmation.
- Do not assume the default download format is correct; confirm the output format when it matters.
