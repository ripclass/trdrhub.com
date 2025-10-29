# Data Models

The data model is structured to capture the entire validation lifecycle and ensure auditability.

- **User**: Manages user accounts.
- **ValidationSession**: The central container for a single validation job.
- **Document**: Represents a single user-uploaded file and its metadata.
- **Discrepancy**: Represents a single issue flagged by the engine.
- **Report**: Represents the final, versioned PDF output of a session, ensuring immutability.
