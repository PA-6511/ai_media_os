export const mockBlocks = [
  {
    id: "block-01",
    name: "Block-A12",
    type: "Ingest",
    status: "running",
    freezeStatus: "active",
    connectionStatus: "connected",
    handshakeStatus: "success",
    updatedAt: "2026-03-16T09:41:00Z"
  },
  {
    id: "block-02",
    name: "Block-B04",
    type: "Analyzer",
    status: "stopped",
    freezeStatus: "frozen",
    connectionStatus: "disconnected",
    handshakeStatus: "idle",
    updatedAt: "2026-03-16T09:18:00Z"
  },
  {
    id: "block-03",
    name: "Block-C07",
    type: "Export",
    status: "warning",
    freezeStatus: "active",
    connectionStatus: "disconnected",
    handshakeStatus: "pending",
    updatedAt: "2026-03-16T09:32:00Z"
  },
  {
    id: "block-04",
    name: "Block-D15",
    type: "Archive",
    status: "running",
    freezeStatus: "frozen",
    connectionStatus: "connected",
    handshakeStatus: "failed",
    updatedAt: "2026-03-16T08:56:00Z"
  }
];

export const auditLogs = [
  {
    id: "log-001",
    timestamp: "2026-03-16T09:41:00Z",
    action: "connect",
    target: "block-01",
    result: "ok",
    operator: "admin"
  },
  {
    id: "log-002",
    timestamp: "2026-03-16T09:32:00Z",
    action: "disconnect",
    target: "block-03",
    result: "ok",
    operator: "admin"
  },
  {
    id: "log-003",
    timestamp: "2026-03-16T09:18:00Z",
    action: "freeze",
    target: "block-02",
    result: "ok",
    operator: "ops-user"
  },
  {
    id: "log-004",
    timestamp: "2026-03-16T08:56:00Z",
    action: "export",
    target: "block-04",
    result: "ok",
    operator: "admin"
  }
];

export const mockAuthConfig = {
  requiredPassword: "pass-1234",
  requiredTwoFactorCode: "000000",
  exportConfirmationText: "EXPORT",
  deleteConfirmationText: "DELETE"
};

export const securitySettings = {
  passwordProtectionEnabled: true,
  twoFactorEnabled: true,
  auditLogRetentionDays: 90,
  handshakeRequired: true,
  dangerousActionLock: true
};