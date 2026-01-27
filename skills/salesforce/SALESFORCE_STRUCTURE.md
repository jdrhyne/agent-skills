# Salesforce Structure Documentation

> **Template:** Fill in this document with your org's specific objects, fields, and business logic.
> The more detail you provide, the better the AI can understand and query your Salesforce data.

---

## Purpose and Scope

This document explains the complete structure of your Salesforce instance, including:
- How each object is defined and used
- Field definitions and relationships
- Business logic and processes
- Org-specific customizations

**Assumed Knowledge:** The AI has access to standard Salesforce documentation and understands basic concepts (objects, fields, relationships, record types). This document focuses on your **org-specific** customizations and business logic.

---

## Company Context

<!-- Update with your company details -->

**Company:** [Your Company Name]
**Industry:** [e.g., B2B SaaS, E-commerce, Financial Services]
**Business Model:** [e.g., Subscription-based, Usage-based, One-time purchase]

**Key Business Characteristics:**
- [ ] Subscription-based revenue (ARR/ACV metrics)
- [ ] Multi-year contracts
- [ ] Usage-based pricing
- [ ] Enterprise and mid-market focus
- [ ] Self-serve / PLG motion
- [ ] Channel / partner sales

---

## Object Hierarchy and Relationships

### Core Objects

```
Lead → (converts to) → Account + Contact + Opportunity

Account (company)
├── Contacts (people)
├── Opportunities (deals)
├── Cases (support tickets)
└── [Custom Objects]

Opportunity (deal)
├── Opportunity Products (line items)
├── Contacts (via Opportunity Contact Roles)
└── [Related Custom Objects]
```

### Opportunity Record Types

<!-- List your record types and their purposes -->

| Record Type | Purpose | Key Rules |
|------------|---------|-----------|
| New | First-time purchase | |
| Renewal | Subscription continuation | |
| Upsell | Adding to existing subscription | |
| Expansion | | |
| Professional Services | | |
| [Add yours] | | |

---

## Object Definitions

### Account

**Purpose:** Represents a company/organization.

**Key Standard Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| Account Name | `Name` | Text | Company name |
| Industry | `Industry` | Picklist | Industry classification |
| Annual Revenue | `AnnualRevenue` | Currency | Annual revenue |
| Website | `Website` | URL | Company website |
| Account Owner | `OwnerId` | Lookup(User) | Sales rep |

**Key Custom Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| | `__c` | | |
| | `__c` | | |

<!-- Add your custom fields -->

---

### Contact

**Purpose:** Represents a person at an Account.

**Key Standard Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| Name | `Name` | Text | Full name |
| Email | `Email` | Email | Email address |
| Title | `Title` | Text | Job title |
| Account | `AccountId` | Lookup(Account) | Parent account |

**Key Custom Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| | `__c` | | |

---

### Opportunity

**Purpose:** Represents a deal/transaction.

**Key Standard Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| Opportunity Name | `Name` | Text | Deal name |
| Amount | `Amount` | Currency | Deal value |
| Stage | `StageName` | Picklist | Sales stage |
| Close Date | `CloseDate` | Date | Expected close |
| Account | `AccountId` | Lookup(Account) | Parent account |
| Record Type | `RecordTypeId` | RecordType | Deal type |
| Is Closed | `IsClosed` | Boolean | Whether deal is closed |
| Is Won | `IsWon` | Boolean | Whether deal was won |

**Key Custom Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| ACV | `ACV__c` | Currency | Annual Contract Value |
| ARR | `ARR__c` | Currency | Annual Recurring Revenue |
| TCV | `TCV__c` | Currency | Total Contract Value |
| LOB | `LOB__c` | Picklist | Line of Business / Product |
| | `__c` | | |

<!-- Add all your important custom fields -->

---

### Opportunity Stages

<!-- Document your sales stages -->

| Stage | Type | Probability | Description |
|-------|------|-------------|-------------|
| Prospecting | Open | 10% | Initial outreach |
| Qualification | Open | 25% | Needs identified |
| Proposal | Open | 50% | Proposal sent |
| Negotiation | Open | 75% | Terms being negotiated |
| Closed Won | Closed/Won | 100% | Deal won |
| Closed Lost | Closed/Lost | 0% | Deal lost |

---

### Lead

**Purpose:** Represents a potential customer before conversion.

**Key Standard Fields:**
| Field | API Name | Type | Description |
|-------|----------|------|-------------|
| Name | `Name` | Text | Full name |
| Company | `Company` | Text | Company name |
| Email | `Email` | Email | Email address |
| Lead Source | `LeadSource` | Picklist | Where they came from |
| Status | `Status` | Picklist | Lead status |

---

## Business Logic

### Deal Flow
<!-- Document how deals progress through your system -->

```
1. Lead Created (inbound/outbound)
2. Lead Qualified → Convert to Account + Contact + Opportunity
3. Opportunity progresses through stages
4. Closed Won → [What happens next?]
   - Renewal opportunity created?
   - Provisioning triggered?
   - Customer success assigned?
```

### Multi-Year Deals
<!-- If applicable, document how multi-year deals are handled -->

```
- SSD (Subscription Start Date) = Start of subscription
- SED (Subscription End Date) = End of Year 1 only
- USED (Ultimate Subscription End Date) = Actual contract end
- TCV = Full multi-year value (manually entered)
- ACV = Annual value (calculated from SSD/SED)
```

### Renewal Process
<!-- Document your renewal process -->

```
1. Original deal closes (New/Upsell)
2. Renewal opportunity auto-created [X] days before SED
3. Renewal linked via Governing Opportunity field
4. Expected Renewal Amount = ACV from governing deal
```

### Revenue Recognition
<!-- Document any revenue recognition rules -->

---

## Reporting Patterns

### Key Metrics
- **Pipeline:** Open opportunities by stage
- **ARR:** Sum of ARR for active subscriptions
- **ACV:** Annual value of new/renewal deals
- **Churn:** Lost renewals / beginning ARR
- **Net Retention:** (Renewed + Expanded) / Beginning ARR

### Common Report Filters
- **This Quarter's Pipeline:** `IsClosed = false AND CloseDate = THIS_QUARTER`
- **Won This Year:** `StageName = 'Closed Won' AND CloseDate = THIS_YEAR`
- **Upcoming Renewals:** `RecordType.Name = 'Renewal' AND CloseDate = NEXT_90_DAYS`

---

## Integrations

<!-- Document any integrations that affect Salesforce data -->

| System | Direction | What Syncs |
|--------|-----------|------------|
| [e.g., HubSpot] | → Salesforce | Leads, Marketing data |
| [e.g., Stripe] | ↔ Salesforce | Payments, Subscriptions |
| [e.g., Zendesk] | ← Salesforce | Account info for tickets |
| [e.g., Gong] | ← Salesforce | Opportunity data for calls |

---

## Notes

<!-- Add any other org-specific notes, gotchas, or important context -->

- 
- 
- 
