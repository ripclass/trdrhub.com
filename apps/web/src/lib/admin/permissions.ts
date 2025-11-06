import { AdminSection } from "./types";

export type AdminPermission =
  | "admin:read"
  | "admin:write"
  | "ops:read"
  | "ops:write"
  | "jobs:read"
  | "jobs:write"
  | "alerts:read"
  | "alerts:write"
  | "audit:read"
  | "audit:write"
  | "approvals:read"
  | "approvals:write"
  | "compliance:read"
  | "compliance:write"
  | "users:read"
  | "users:write"
  | "api_keys:read"
  | "api_keys:write"
  | "sessions:read"
  | "sessions:write"
  | "billing:read"
  | "billing:write"
  | "disputes:read"
  | "disputes:write"
  | "partners:read"
  | "partners:write"
  | "webhooks:read"
  | "webhooks:write"
  | "llm:read"
  | "llm:write"
  | "legal_holds:read"
  | "legal_holds:write"
  | "feature_flags:read"
  | "feature_flags:write"
  | "releases:read"
  | "releases:write"
  | "settings:read"
  | "settings:write"
  | "billing_adjustments:write"
  | "billing_disputes:write";

export interface SectionPermissionConfig {
  view: AdminPermission[];
  actions?: Record<string, AdminPermission[]>;
}

export const SECTION_PERMISSIONS: Record<AdminSection, SectionPermissionConfig> = {
  overview: {
    view: ["admin:read"],
  },
  "ops-monitoring": {
    view: ["ops:read"],
  },
  "ops-jobs": {
    view: ["jobs:read"],
    actions: {
      retry: ["jobs:write"],
      cancel: ["jobs:write"],
    },
  },
  "ops-alerts": {
    view: ["alerts:read"],
    actions: {
      acknowledge: ["alerts:write"],
      snooze: ["alerts:write"],
    },
  },
  "audit-logs": {
    view: ["audit:read"],
  },
  "audit-approvals": {
    view: ["approvals:read"],
    actions: {
      approve: ["approvals:write"],
      reject: ["approvals:write"],
    },
  },
  "audit-compliance": {
    view: ["compliance:read"],
    actions: {
      export: ["compliance:read"],
    },
  },
  "security-users": {
    view: ["users:read"],
    actions: {
      invite: ["users:write"],
      disable: ["users:write"],
      updateRole: ["users:write"],
    },
  },
  "security-access": {
    view: ["api_keys:read"],
    actions: {
      create: ["api_keys:write"],
      rotate: ["api_keys:write"],
      revoke: ["api_keys:write"],
    },
  },
  "security-sessions": {
    view: ["sessions:read"],
    actions: {
      revoke: ["sessions:write"],
    },
  },
  "billing-plans": {
    view: ["billing:read"],
    actions: {
      update: ["billing:write"],
    },
  },
  "billing-adjustments": {
    view: ["billing:read"],
    actions: {
      create: ["billing_adjustments:write"],
    },
  },
  "billing-disputes": {
    view: ["disputes:read"],
    actions: {
      resolve: ["billing_disputes:write"],
    },
  },
  "partners-registry": {
    view: ["partners:read"],
    actions: {
      toggle: ["partners:write"],
    },
  },
  "partners-connectors": {
    view: ["partners:read"],
    actions: {
      update: ["partners:write"],
    },
  },
  "partners-webhooks": {
    view: ["webhooks:read"],
    actions: {
      redeliver: ["webhooks:write"],
      rotate: ["webhooks:write"],
    },
  },
  "llm-prompts": {
    view: ["llm:read"],
    actions: {
      publish: ["llm:write"],
    },
  },
  "llm-budgets": {
    view: ["llm:read"],
    actions: {
      update: ["llm:write"],
    },
  },
  "llm-evaluations": {
    view: ["llm:read"],
  },
  "compliance-residency": {
    view: ["compliance:read"],
    actions: {
      update: ["compliance:write"],
    },
  },
  "compliance-retention": {
    view: ["compliance:read"],
    actions: {
      run: ["compliance:write"],
    },
  },
  "compliance-legal-holds": {
    view: ["legal_holds:read"],
    actions: {
      create: ["legal_holds:write"],
      release: ["legal_holds:write"],
    },
  },
  "system-feature-flags": {
    view: ["feature_flags:read"],
    actions: {
      update: ["feature_flags:write"],
    },
  },
  "system-releases": {
    view: ["releases:read"],
  },
  "system-settings": {
    view: ["settings:read"],
    actions: {
      update: ["settings:write"],
    },
  },
};

export function hasAnyPermission(current: string[], required: AdminPermission[]): boolean {
  if (!required.length) return true;
  if (current.includes("*")) return true;
  return required.some((permission) => current.includes(permission));
}

export function canViewSection(section: AdminSection, current: string[]): boolean {
  const config = SECTION_PERMISSIONS[section];
  if (!config) return false;
  return hasAnyPermission(current, config.view);
}

export function canPerformAction(
  section: AdminSection,
  action: string,
  current: string[],
): boolean {
  const config = SECTION_PERMISSIONS[section];
  if (!config?.actions) return false;
  const required = config.actions[action];
  if (!required) return false;
  return hasAnyPermission(current, required);
}

export function listPermittedSections(current: string[]): AdminSection[] {
  return (Object.keys(SECTION_PERMISSIONS) as AdminSection[]).filter((section) =>
    canViewSection(section, current),
  );
}

