// === 接続先設定 ===
// 疎通確認: ブラウザで ${API_BASE_URL}/blocks にアクセスして JSON が返るか確認
export const API_BASE_URL = "/api";

// === 使用 API path 一覧 (Step1: 一覧取得系) ===
// GET /blocks        -> getBlocksJson() / getJson("/blocks")
// GET /blocks/{id}   -> blockService が getJson(`/blocks/${id}`) で直接呼ぶ
export const API_PATHS = {
	blocks: "/blocks",
	// Step2: 詳細取得系で使用する /blocks/{id}
	blockById: (id) => `/blocks/${encodeURIComponent(String(id ?? ""))}`,
	// Step3: 接続/切断系で使用する /blocks/{id}/connect|disconnect
	// Network タブで表示される URL: /api/blocks/{id}/connect または /api/blocks/{id}/disconnect
	blockConnect:    (id) => `/blocks/${encodeURIComponent(String(id ?? ""))}/connect`,
	blockDisconnect: (id) => `/blocks/${encodeURIComponent(String(id ?? ""))}/disconnect`,
	// Step5: freeze/unfreeze 系で使用する /blocks/{id}/freeze|unfreeze
	blockFreeze: (id) => `/blocks/${encodeURIComponent(String(id ?? ""))}/freeze`,
	blockUnfreeze: (id) => `/blocks/${encodeURIComponent(String(id ?? ""))}/unfreeze`,
	// Step4: Audit Log / Security Settings 系
	auditLogs: "/audit-logs",
	securitySettings: "/settings/security"
};

// Step3 実動確認で使う POST endpoint を明示
export const STEP3_POST_PATHS = {
	connect: "POST /blocks/{id}/connect",
	disconnect: "POST /blocks/{id}/disconnect"
};

// Step5 実動確認で使う POST endpoint を明示
export const STEP5_POST_PATHS = {
	freeze: "POST /blocks/{id}/freeze",
	unfreeze: "POST /blocks/{id}/unfreeze"
};

// Step3 では body 未指定でも {} を JSON として送る方針を維持する
export const STEP3_POST_REQUEST_BODY = {
	connect: "{} when omitted",
	disconnect: "{} when omitted"
};

// Step2 (詳細取得系) の呼び出し追跡用: /blocks/{id} を一箇所で生成
export function getBlockByIdPath(id) {
	return API_PATHS.blockById(id);
}

// Step3 (接続/切断系) の呼び出し追跡用 path 生成
export function getBlockConnectPath(id) {
	return API_PATHS.blockConnect(id);
}

export function getBlockDisconnectPath(id) {
	return API_PATHS.blockDisconnect(id);
}

export function getBlockFreezePath(id) {
	return API_PATHS.blockFreeze(id);
}

export function getBlockUnfreezePath(id) {
	return API_PATHS.blockUnfreeze(id);
}

export function buildApiUrl(path) {
	const normalizedPath = String(path ?? "").startsWith("/") ? String(path) : `/${String(path ?? "")}`;
	return `${API_BASE_URL}${normalizedPath}`;
}

// Step3 の疎通確認で、Network に出る最終 URL をコード上でも追えるようにする
export function getBlockConnectUrl(id) {
	return buildApiUrl(getBlockConnectPath(id));
}

export function getBlockDisconnectUrl(id) {
	return buildApiUrl(getBlockDisconnectPath(id));
}

export function getBlockFreezeUrl(id) {
	return buildApiUrl(getBlockFreezePath(id));
}

export function getBlockUnfreezeUrl(id) {
	return buildApiUrl(getBlockUnfreezePath(id));
}

// Step3 疎通確認用: path/url と body 有無をコード上で追いやすくする
export function getStep3PostDebugInfo(id, body = {}) {
	const requestBody = body ?? {};

	return {
		connect: {
			method: "POST",
			path: getBlockConnectPath(id),
			url: getBlockConnectUrl(id),
			requestBody,
			hasRequestBody: requestBody != null
		},
		disconnect: {
			method: "POST",
			path: getBlockDisconnectPath(id),
			url: getBlockDisconnectUrl(id),
			requestBody,
			hasRequestBody: requestBody != null
		}
	};
}

// Step5 疎通確認用: freeze/unfreeze の path/url と body 有無を追いやすくする
export function getStep5PostDebugInfo(id, body = {}) {
	const requestBody = body ?? {};

	return {
		freeze: {
			method: "POST",
			path: getBlockFreezePath(id),
			url: getBlockFreezeUrl(id),
			requestBody,
			hasRequestBody: requestBody != null
		},
		unfreeze: {
			method: "POST",
			path: getBlockUnfreezePath(id),
			url: getBlockUnfreezeUrl(id),
			requestBody,
			hasRequestBody: requestBody != null
		}
	};
}

export async function getJson(path) {
	const response = await fetch(buildApiUrl(path), {
		method: "GET",
		headers: {
			Accept: "application/json"
		}
	});

	if (!response.ok) {
		throw new Error(`GET ${path} failed: ${response.status}`);
	}

	return response.json();
}

export async function postJson(path, body = {}) {
	// Network タブで追跡しやすいよう、fetch には buildApiUrl(path) の結果がそのまま渡る。
	// 例: path=/blocks/{id}/connect -> url=/api/blocks/{id}/connect
	// Step3 では body 未指定時も {} を送る (request payload 有無の確認時に意図を追いやすくする)。
	const response = await fetch(buildApiUrl(path), {
		method: "POST",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json"
		},
		body: JSON.stringify(body ?? {})
	});

	if (!response.ok) {
		throw new Error(`POST ${path} failed: ${response.status}`);
	}

	return response.json();
}

export async function putJson(path, body = {}) {
	const response = await fetch(buildApiUrl(path), {
		method: "PUT",
		headers: {
			Accept: "application/json",
			"Content-Type": "application/json"
		},
		body: JSON.stringify(body ?? {})
	});

	if (!response.ok) {
		throw new Error(`PUT ${path} failed: ${response.status}`);
	}

	return response.json();
}

// GET /blocks
export function getBlocksJson() {
	return getJson(API_PATHS.blocks);
}

// Step2 実動確認用: 詳細取得 path と GET 呼び出しを apiClient 上で追いやすくする
// 既存の fetch 方針は維持し、利用側が必要ならこの関数を選べる形にとどめる
export function getBlockByIdJson(id) {
	return getJson(getBlockByIdPath(id));
}

// === Step4: Audit Log / Security Settings API ===
// Step4 実動確認で使う endpoint を明示
export const STEP4_AUDIT_SETTINGS_PATHS = {
	auditLogs: "GET /audit-logs",
	securitySettingsGet: "GET /settings/security",
	securitySettingsPut: "PUT /settings/security"
};

export function getAuditLogsJson() {
	return getJson(API_PATHS.auditLogs);
}

export function getAuditLogsPath() {
	return API_PATHS.auditLogs;
}

function appendQuery(path, query = {}) {
	const params = new URLSearchParams();

	for (const [key, value] of Object.entries(query ?? {})) {
		if (value == null) continue;
		const text = String(value).trim();
		if (!text) continue;
		params.append(key, text);
	}

	const qs = params.toString();
	return qs ? `${path}?${qs}` : path;
}

export function getAuditLogsPathByQuery(query = {}) {
	return appendQuery(API_PATHS.auditLogs, query);
}

export function getAuditLogsByQueryJson(query = {}) {
	return getJson(getAuditLogsPathByQuery(query));
}

export function getAuditLogCountJson(query = {}) {
	return getJson(appendQuery(`${API_PATHS.auditLogs}/count`, query));
}

export function getAuditLogsUrl(query = {}) {
	return buildApiUrl(getAuditLogsPathByQuery(query));
}

export function getSecuritySettingsJson() {
	return getJson(API_PATHS.securitySettings);
}

export function getSecuritySettingsPath() {
	return API_PATHS.securitySettings;
}

export function getSecuritySettingsUrl() {
	return buildApiUrl(getSecuritySettingsPath());
}

export function updateSecuritySettingsJson(body = {}) {
	return putJson(API_PATHS.securitySettings, body);
}

// Step4 疎通確認用: Audit/Settings の path/url/body 有無をコード上で追いやすくする
export function getStep4AuditSettingsDebugInfo(options = {}) {
	const query = options?.query ?? {};
	const requestBody = options?.body ?? {};

	return {
		auditLogs: {
			method: "GET",
			path: getAuditLogsPathByQuery(query),
			url: getAuditLogsUrl(query),
			hasRequestBody: false
		},
		securitySettingsGet: {
			method: "GET",
			path: getSecuritySettingsPath(),
			url: getSecuritySettingsUrl(),
			hasRequestBody: false
		},
		securitySettingsPut: {
			method: "PUT",
			path: getSecuritySettingsPath(),
			url: getSecuritySettingsUrl(),
			requestBody,
			hasRequestBody: requestBody != null
		}
	};
}

// === Step3: 接続/切断系 POST API ===
// Network タブ確認: fetch URL は buildApiUrl(API_PATHS.blockConnect/blockDisconnect(id)) として表示される
// Console 確認: postJson() の err throw で "POST {path} failed" をフィルターできる

export function connectBlockJson(id, body = {}) {
	// POST /blocks/{id}/connect
	// 送信先: /api/blocks/{id}/connect
	// リクエストボディ: {} (空 object も JSON.stringify で送信)
	return postJson(getBlockConnectPath(id), body);
}

export function disconnectBlockJson(id, body = {}) {
	// POST /blocks/{id}/disconnect
	// 送信先: /api/blocks/{id}/disconnect
	// リクエストボディ: {} (空 object も JSON.stringify で送信)
	return postJson(getBlockDisconnectPath(id), body);
}

// === Step5: freeze / unfreeze 系 POST API ===
// Network タブ確認: fetch URL は buildApiUrl(API_PATHS.blockFreeze/blockUnfreeze(id)) として表示される
// Console 確認: postJson() の err throw で "POST {path} failed" をフィルターできる
// request body: {} (空 object を JSON.stringify で送信)

export function freezeBlockJson(id, body = {}) {
	// POST /blocks/{id}/freeze (レガシー互換、blockService は postJson 直接使用)
	// 送信先: /api/blocks/{id}/freeze
	// body: {} — blockService 側から直接 postJson() を呼ぶ場合も同じ body を渡す
	return postJson(getBlockFreezePath(id), body);
}

export function unfreezeBlockJson(id, body = {}) {
	// POST /blocks/{id}/unfreeze (レガシー互換、blockService は postJson 直接使用)
	// 送信先: /api/blocks/{id}/unfreeze
	// body: {} — blockService 側から直接 postJson() を呼ぶ場合も同じ body を渡す
	return postJson(getBlockUnfreezePath(id), body);
}