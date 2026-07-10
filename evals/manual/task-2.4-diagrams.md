# Manual test — Task 2.4 (10 varied Mermaid diagrams for Obsidian rendering)

Open this file in Obsidian (reading or live-preview mode). **Pass = all 10 diagrams render with no "Syntax error" box, in both light and dark theme.** Each diagram is the kind `alexandria-teach` would emit for the named explanation, and each follows every constraint in `references/diagrams.md`.

Machine pre-check (2026-07-09): all 10 blocks extracted and rendered to SVG by `@mermaid-js/mermaid-cli` 11.16.0 with zero parse errors. The Obsidian visual pass (this file, both themes) is the remaining DOD step.

## 1. Architecture — the Alexandria suite (flowchart TD)

```mermaid
flowchart TD
    user[User] --> teach[alexandria-teach]
    teach --> agent[alexandria-teacher subagent]
    teach --> recall[alexandria-recall]
    teach --> librarian[alexandria-librarian]
    librarian --> vaultpy["scripts/vault.py"]
    recall --> vault[(Obsidian vault)]
    vaultpy --> vault
```

## 2. Data flow — webhook receive-then-process (flowchart LR)

```mermaid
flowchart LR
    gateway[Payment gateway] -->|POST JSON| controller[Webhook controller]
    controller -->|insert row| table[(webhook_event table)]
    controller -->|"200 {received: true}"| gateway
    cron[Cron job] -->|read unprocessed| table
    cron -->|apply event| order[Order]
```

## 3. Call sequence — checkout tokenization (sequenceDiagram)

```mermaid
sequenceDiagram
    participant B as Shopper browser
    participant G as Gateway
    participant S as Store server
    B->>G: card number
    G-->>B: token
    B->>S: checkout form plus token
    S->>G: charge with token
    G-->>S: approved
```

## 4. Call sequence with branches — retry with backoff (sequenceDiagram, alt/loop)

```mermaid
sequenceDiagram
    participant J as Job runner
    participant S as External service
    loop until success or max attempts
        J->>S: attempt job
        alt service responds
            S-->>J: success
        else timeout
            S--xJ: no response
            Note over J: wait 1s, 2s, 4s...
        end
    end
```

## 5. State machine — payment lifecycle (stateDiagram-v2)

```mermaid
stateDiagram-v2
    [*] --> Authorized
    Authorized --> Captured : capture
    Authorized --> Voided : void
    Captured --> Refunded : refund
    Captured --> ChargedBack : chargeback
    Voided --> [*]
    Refunded --> [*]
    ChargedBack --> [*]
```

## 6. Class relations — gateway commands (classDiagram)

```mermaid
classDiagram
    class CommandInterface {
        +execute(subject)
    }
    class SaleCommand {
        +execute(subject)
    }
    class RefundCommand {
        +execute(subject)
    }
    class VoidCommand {
        +execute(subject)
    }
    CommandInterface <|.. SaleCommand
    CommandInterface <|.. RefundCommand
    CommandInterface <|.. VoidCommand
    SaleCommand --> IqProClient : uses
```

## 7. Data model — webhook events and orders (erDiagram)

```mermaid
erDiagram
    SALES_ORDER ||--o{ WEBHOOK_EVENT : "updated by"
    WEBHOOK_EVENT {
        int id
        string trace_id
        string resource_type
        string status
        bool processed
    }
    SALES_ORDER {
        int entity_id
        string increment_id
        string state
    }
```

## 8. Grouped architecture — vault layout (flowchart TD, subgraphs)

```mermaid
flowchart TD
    subgraph vault [Vault root]
        welcome[Welcome.md]
        subgraph proj [Project folder]
            idx[_index.md]
            glos[_glossary.md]
            sess[Sessions notes]
        end
        subgraph conc [_Concepts]
            shared[Shared concept files]
        end
    end
    sess --> glos
    glos --> shared
    idx --> sess
```

## 9. Proportions — token budget by session type (pie)

```mermaid
pie title Token budget share by session type
    "Simple walkthrough" : 25
    "Concept-heavy lesson" : 45
    "Recall-assisted session" : 30
```

## 10. Schedule — build phases (gantt)

```mermaid
gantt
    title Alexandria build order
    dateFormat YYYY-MM-DD
    section Foundations
    Phase 0 :p0, 2026-07-09, 3d
    Phase 1 :p1, after p0, 4d
    section Skills
    Phase 2 teach :p2, after p1, 7d
    Phase 3 librarian :p3, after p2, 7d
    Phase 4 recall :p4, after p3, 5d
```

---

## Syntax patterns deliberately avoided, and why

| Avoided | Why |
|---|---|
| `%%{init: {...}}%%` directives, `style`/`classDef`/`linkStyle` | Fights Obsidian's light/dark theming — renders unreadable in one of the two modes |
| Unquoted labels with `( ) { } : ,` | Parse error in several Mermaid versions — quoted form used everywhere (diagrams 1, 2) |
| HTML in labels (`<br/>`, `<b>`) | Inconsistent across Mermaid versions/sanitizers; short labels instead |
| A node ID named `end` | Reserved word in flowchart/sequence blocks — breaks the parser |
| `click` handlers, Font Awesome `fa:fa-*` icons | Interactivity and icon fonts are not available in Obsidian's Mermaid sandbox |
| `mindmap`, `timeline`, `quadrantChart`, `sankey`, `xychart`, `block-beta` | Newer diagram types; Obsidian's bundled Mermaid may predate them — silent hard failure |
| Legacy `stateDiagram` (v1) and bare `graph` | v2/flowchart are the maintained grammars with better Obsidian rendering |
| `autonumber` in sequence diagrams | Adds step numbers the prose doesn't reference; noise |
| Trailing semicolons, multi-statement lines | Version-sensitive parsing; one statement per line throughout |
