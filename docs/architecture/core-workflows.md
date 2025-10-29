# Core Workflows

The primary workflow is asynchronous to handle long-running tasks and large files gracefully, with explicit error handling paths using SQS Dead Letter Queues (DLQs) for failed jobs.
