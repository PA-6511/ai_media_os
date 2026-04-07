import { auditLogs, securitySettings } from "../data/mock-data.js";
import {
	getAuditLogCountJson,
	getAuditLogsByQueryJson,
	getAuditLogsJson,
	getSecuritySettingsJson,
	updateSecuritySettingsJson
} from "./apiClient.js";

// API差し替え設計メモ（実装はまだ mock 維持）
// - getAuditLogs: GET /audit-logs
// - getRecentAuditLogs: GET /audit-logs?limit={n}
// - getAuditLogViewItems: GET /audit-logs?action={action}&result={result}
// - getAuditLogCount: GET /audit-logs/count?action={action}&result={result}
// - appendAuditLog: POST /audit-logs
// - getSecuritySettings: GET /settings/security
// - updateSecuritySettings: PUT /settings/security

function pickString(value, fallback) {
	if (typeof value !== "string") return fallback;
	const normalized = value.trim();
	return normalized || fallback;
}

function createAuditLogId() {
	const lastLogId = auditLogs[auditLogs.length - 1]?.id ?? "log-000";
	const lastSequence = Number.parseInt(lastLogId.replace(/^log-/, ""), 10);
	const nextSequence = Number.isNaN(lastSequence) ? auditLogs.length + 1 : lastSequence + 1;
	return `log-${String(nextSequence).padStart(3, "0")}`;
}

function normalizeAuditLogFilter(filter = {}) {
	return {
		action: pickString(filter?.action, "").toLowerCase(),
		result: pickString(filter?.result, "").toLowerCase()
	};
}

function matchesAuditLogFilter(log, filter) {
	if (filter.action && !log.action.toLowerCase().includes(filter.action)) {
		return false;
	}

	if (filter.result && !log.result.toLowerCase().includes(filter.result)) {
		return false;
	}

	return true;
}

function toAuditLogViewItem(log) {
	return {
		id: pickString(log?.id, "log-000"),
		timestamp: pickString(log?.timestamp, "-"),
		action: pickString(log?.action, "unknown"),
		target: pickString(log?.target, "-"),
		result: pickString(log?.result, "ok"),
		operator: pickString(log?.operator, "system")
	};
}

function cloneMockAuditLogs() {
	return auditLogs.map((log) => ({ ...log }));
}

function normalizeAuditLog(log) {
	return {
		id: pickString(log?.id, createAuditLogId()),
		timestamp: pickString(log?.timestamp, new Date().toISOString()),
		action: pickString(log?.action, "unknown"),
		target: pickString(log?.target, "-"),
		result: pickString(log?.result, "ok"),
		operator: pickString(log?.operator, "system")
	};
}

function normalizeSecuritySettings(input = {}, fallback = securitySettings) {
	return {
		passwordProtectionEnabled: Boolean(input?.passwordProtectionEnabled ?? fallback.passwordProtectionEnabled),
		twoFactorEnabled: Boolean(input?.twoFactorEnabled ?? fallback.twoFactorEnabled),
		auditLogRetentionDays: Number.isFinite(Number(input?.auditLogRetentionDays))
			? Number(input.auditLogRetentionDays)
			: fallback.auditLogRetentionDays,
		handshakeRequired: Boolean(input?.handshakeRequired ?? fallback.handshakeRequired),
		dangerousActionLock: Boolean(input?.dangerousActionLock ?? fallback.dangerousActionLock)
	};
}

function resolveSecuritySettingsResponse(response) {
	if (response && typeof response === "object") {
		if (response.data && typeof response.data === "object") {
			return response.data;
		}
		return response;
	}

	return null;
}

function resolveAuditLogsResponse(response) {
	if (Array.isArray(response)) {
		return response;
	}

	if (Array.isArray(response?.data?.items)) {
		return response.data.items;
	}

	if (Array.isArray(response?.data?.logs)) {
		return response.data.logs;
	}

	if (Array.isArray(response?.items)) {
		return response.items;
	}

	if (Array.isArray(response?.logs)) {
		return response.logs;
	}

	return null;
}

function resolveAuditLogCountResponse(response) {
	if (typeof response === "number" && Number.isFinite(response)) {
		return response;
	}

	if (typeof response?.count === "number" && Number.isFinite(response.count)) {
		return response.count;
	}

	if (typeof response?.data?.count === "number" && Number.isFinite(response.data.count)) {
		return response.data.count;
	}

	return null;
}

function toAuditLogQuery(filter = {}) {
	const normalizedFilter = normalizeAuditLogFilter(filter);
	return {
		action: normalizedFilter.action || undefined,
		result: normalizedFilter.result || undefined
	};
}

function toAuditLogViewItemsFromLogs(logs, filter = {}) {
	const normalizedFilter = normalizeAuditLogFilter(filter);

	return [...logs]
		.reverse()
		.map((log) => toAuditLogViewItem(log))
		.filter((log) => matchesAuditLogFilter(log, normalizedFilter));
}

// API差し替えポイント: GET /audit-logs
export async function getAuditLogs() {
	const fallbackLogs = cloneMockAuditLogs();

	try {
		// 将来は getJson('/audit-logs') の直接利用へ寄せる前提で、現段階は apiClient 経由。
		const response = await getAuditLogsJson();
		const apiLogs = resolveAuditLogsResponse(response);

		// API成功: 配列として解決できた場合のみAPI結果を採用
		if (!Array.isArray(apiLogs)) {
			// API失敗扱い: 応答shape不一致は fallback
			return fallbackLogs;
		}

		return apiLogs.map((log) => normalizeAuditLog(log));
	} catch {
		// API通信失敗時は fallback
		return fallbackLogs;
	}
}

// API差し替えポイント: GET /audit-logs?action={action}&result={result}
export async function getAuditLogViewItems(filter = {}) {
	const query = toAuditLogQuery(filter);

	try {
		const response = await getAuditLogsByQueryJson(query);
		const apiLogs = resolveAuditLogsResponse(response);

		// API成功: 条件付き一覧をAPI応答から構築
		if (Array.isArray(apiLogs)) {
			const normalizedLogs = apiLogs.map((log) => normalizeAuditLog(log));
			return toAuditLogViewItemsFromLogs(normalizedLogs, filter);
		}
	} catch {
		// no-op: fallback below
	}

	// API失敗/shape不一致時は getAuditLogs() 経由で fallback（mock含む）
	const logs = await getAuditLogs();
	return toAuditLogViewItemsFromLogs(logs, filter);
}

// API差し替えポイント: GET /audit-logs/count?action={action}&result={result}
export async function getAuditLogCount(filter = {}) {
	const query = toAuditLogQuery(filter);

	try {
		const response = await getAuditLogCountJson(query);
		const count = resolveAuditLogCountResponse(response);

		// API成功: count を直接採用
		if (typeof count === "number") {
			return count;
		}
	} catch {
		// no-op: fallback below
	}

	// API失敗/shape不一致時は view items から件数を算出
	const logs = await getAuditLogViewItems(filter);
	return logs.length;
}

// API差し替えポイント: GET /audit-logs?limit={n}
export async function getRecentAuditLogs(limit = 5) {
	const normalizedLimit = Number.isFinite(Number(limit)) ? Math.max(0, Number(limit)) : 5;
	// getAuditLogViewItems() 側で API成功/失敗の吸収を行う
	const logs = await getAuditLogViewItems({});
	return logs.slice(0, normalizedLimit);
}

// API差し替えポイント: POST /audit-logs（本番ではサーバ責務寄せの可能性あり）
export function appendAuditLog(entry) {
	const nextLog = {
		id: pickString(entry?.id, createAuditLogId()),
		timestamp: pickString(entry?.timestamp, new Date().toISOString()),
		action: pickString(entry?.action, "unknown"),
		target: pickString(entry?.target, "-"),
		result: pickString(entry?.result, "ok"),
		operator: pickString(entry?.operator, "system")
	};

	auditLogs.push(nextLog);
	return Promise.resolve({ ...nextLog });
}

// API差し替えポイント: GET /settings/security
export async function getSecuritySettings() {
	try {
		// 将来は getJson('/settings/security') の直接利用へ寄せる前提で、現段階は apiClient 経由。
		const response = await getSecuritySettingsJson();
		const resolved = resolveSecuritySettingsResponse(response);

		// API成功: settings object を解決できた場合は API 結果を採用
		if (resolved) {
			const normalized = normalizeSecuritySettings(resolved);
			Object.assign(securitySettings, normalized);
			return { ...securitySettings };
		}
	} catch {
		// no-op: fallback below
	}

	// API失敗/shape不一致時は既存 settings を返して表示維持
	return { ...securitySettings };
}

// API差し替えポイント: PUT /settings/security
export async function updateSecuritySettings(nextSettings) {
	const normalizedNextSettings = normalizeSecuritySettings(nextSettings);

	try {
		// 将来は putJson('/settings/security', nextSettings) の直接利用へ寄せる前提で、現段階は apiClient 経由。
		const response = await updateSecuritySettingsJson(normalizedNextSettings);
		const resolved = resolveSecuritySettingsResponse(response);
		const normalizedFromApi = resolved
			? normalizeSecuritySettings(resolved, normalizedNextSettings)
			: normalizedNextSettings;

		// API成功: response を優先して local settings へ反映
		Object.assign(securitySettings, normalizedFromApi);
	} catch {
		// API失敗時は fail-safe: 入力値ベースで local settings を更新し UI を壊さない
		Object.assign(securitySettings, normalizedNextSettings);
	}

	await appendAuditLog({
		action: "settings_update",
		target: "security_settings",
		result: "ok",
		operator: pickString(nextSettings?.operator, "local-user")
	});

	return { ...securitySettings };
}
