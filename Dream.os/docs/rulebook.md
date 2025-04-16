### Rule GEN-004: Handling Missing/Conflicting Information
- **ID:** GEN-004
- **Description:** "If required documentation (e.g., format specifications, protocol details) referenced in tasks or guidelines is missing, incorrect, or conflicts with observed system behavior: 1. Attempt to infer correct procedure from context or related files. 2. Report the discrepancy via the standard communication channel (e.g., mailbox, designated outbox file drop) detailing the missing/conflicting information and the location referencing it. 3. If the task is not critically blocked by the missing information, proceed with the task using inferred or observed behavior. 4. Log the event using the governance logger."
- **Keywords:** `missing documentation`, `conflicting information`, `report`, `proceed if possible`, `infer`, `discrepancy`
- **Applies To:** `all_agents`

```yaml
rules:
  - id: GEN-004
    description: "If required documentation (e.g., format specifications, protocol details) referenced in tasks or guidelines is missing, incorrect, or conflicts with observed system behavior: 1. Attempt to infer correct procedure from context or related files. 2. Report the discrepancy via the standard communication channel (e.g., mailbox, designated outbox file drop) detailing the missing/conflicting information and the location referencing it. 3. If the task is not critically blocked by the missing information, proceed with the task using inferred or observed behavior. 4. Log the event using the governance logger."
    keywords:
      - missing documentation
      - conflicting information
      - report
      - proceed if possible
      - infer
      - discrepancy
    applies_to: all_agents
```
--- 