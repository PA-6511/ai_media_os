import { mockAuthConfig, mockBlocks } from "../data/mock-data.js";
import { getBlocksJson, getJson, postJson } from "./apiClient.js";
import { appendAuditLog } from "./logService.js";

// API導線メモ（API結果を優先しつつ mock fallback を併用）
// - getBlocks: GET /blocks
// - getBlockById: GET /blocks/{id}
// - getConnectionManagementItems: GET /blocks を GUI向けに整形
// - getBlockDetailViewModel: GET /blocks/{id} を GUI向けに整形
// - getBlockDashboardStats: GET /blocks を GUI向けに集計
// - connectBlock: POST /blocks/{id}/connect
// - disconnectBlock: POST /blocks/{id}/disconnect
// - freezeBlock: POST /blocks/{id}/freeze
// - unfreezeBlock: POST /blocks/{id}/unfreeze
// - exportBlock: POST /blocks/{id}/export
// - deleteBlock: DELETE /blocks/{id}（互換時: POST /blocks/{id}/delete）
// - getFreezeDangerMeta: GET /blocks/{id} を元に Freeze warning 用メタを生成
// - getLockGuardMeta: GET /blocks/{id} を元に LockGuard 用メタを生成
// - getHandshakeStatus: GET /blocks/{id}/handshake
// - setHandshakeStatus: POST /blocks/{id}/handshake

function createAuditTarget(block, blockId) {
	if (block?.name && block?.id) return `${block.name} (${block.id})`;
	if (block?.name) return block.name;
	return String(blockId);
}

function hasCompletedAuth(authInfo, actionType) {
	const expectedConfirmationText = actionType === "delete"
		? mockAuthConfig.deleteConfirmationText
		: mockAuthConfig.exportConfirmationText;

	const hasRequiredPassword = authInfo?.password === mockAuthConfig.requiredPassword;
	const hasRequiredTwoFactorCode = authInfo?.twoFactorCode === mockAuthConfig.requiredTwoFactorCode;
	const hasConfirmed = authInfo?.confirmed === true;
	const hasRequiredConfirmationText = authInfo?.confirmationText === expectedConfirmationText;
	const hasRequiredConfirmation = hasConfirmed && hasRequiredConfirmationText;

	return Boolean(hasRequiredPassword && hasRequiredTwoFactorCode && hasRequiredConfirmation);
}

function getAuthFailureMessage(authInfo, actionType) {
	const expectedConfirmationText = actionType === "delete"
		? mockAuthConfig.deleteConfirmationText
		: mockAuthConfig.exportConfirmationText;

	if (authInfo?.password !== mockAuthConfig.requiredPassword) {
		return "Authentication failed: password mismatch.";
	}

	if (authInfo?.twoFactorCode !== mockAuthConfig.requiredTwoFactorCode) {
		return "Authentication failed: two-factor code mismatch.";
	}

	if (authInfo?.confirmed !== true) {
		return "Authentication failed: confirmation flag is false.";
	}

	if (authInfo?.confirmationText !== expectedConfirmationText) {
		return "Authentication failed: confirmation text mismatch.";
	}

	return "Authentication is not completed.";
}

function cloneMockBlocks() {
	return mockBlocks.map((block) => ({ ...block }));
}

function resolveBlocksListResponse(response) {
	if (Array.isArray(response)) {
		return response;
	}

	if (Array.isArray(response?.data?.items)) {
		return response.data.items;
	}

	if (Array.isArray(response?.data?.blocks)) {
		return response.data.blocks;
	}

	if (Array.isArray(response?.items)) {
		return response.items;
	}

	if (Array.isArray(response?.blocks)) {
		return response.blocks;
	}

	return null;
}

function resolveBlockDetailResponse(response) {
	if (!response || typeof response !== "object" || Array.isArray(response)) {
		return null;
	}

	if (response?.data?.item && typeof response.data.item === "object" && !Array.isArray(response.data.item)) {
		return response.data.item;
	}

	if (response?.data?.block && typeof response.data.block === "object" && !Array.isArray(response.data.block)) {
		return response.data.block;
	}

	if (response?.item && typeof response.item === "object" && !Array.isArray(response.item)) {
		return response.item;
	}

	if (response?.block && typeof response.block === "object" && !Array.isArray(response.block)) {
		return response.block;
	}

	return response;
}

function getFailedGetStatus(error) {
	const match = String(error?.message ?? "").match(/failed:\s*(\d{3})/);
	return match ? Number(match[1]) : null;
}

const DEFAULT_BLOCK_VALUES = Object.freeze({
	name: "-",
	type: "-",
	status: "stopped",
	connectionStatus: "disconnected",
	freezeStatus: "active",
	handshakeStatus: "idle",
	deleteRequested: false
});

const BLOCK_DETAIL_VIEW_MODEL_FIELDS = Object.freeze([
	"id",
	"name",
	"type",
	"status",
	"connectionStatus",
	"freezeStatus",
	"handshakeStatus",
	"updatedAt",
	"deleteRequested"
]);

// Step2 実動確認用: getBlockDetailViewModel の返却キー確認で再利用する
export const BLOCK_DETAIL_VIEW_MODEL_KEYS = BLOCK_DETAIL_VIEW_MODEL_FIELDS;

// Step2 実動確認用:
// API 詳細レスポンスの欠損項目は fallbackBlock と DEFAULT_BLOCK_VALUES で補完する
function normalizeBlock(apiBlock, fallbackBlock = {}) {
	return {
		id: String(apiBlock?.id ?? fallbackBlock.id ?? ""),
		name: apiBlock?.name ?? fallbackBlock.name ?? DEFAULT_BLOCK_VALUES.name,
		type: apiBlock?.type ?? fallbackBlock.type ?? DEFAULT_BLOCK_VALUES.type,
		status: apiBlock?.status ?? fallbackBlock.status ?? DEFAULT_BLOCK_VALUES.status,
		connectionStatus: apiBlock?.connectionStatus ?? fallbackBlock.connectionStatus ?? DEFAULT_BLOCK_VALUES.connectionStatus,
		freezeStatus: apiBlock?.freezeStatus ?? fallbackBlock.freezeStatus ?? DEFAULT_BLOCK_VALUES.freezeStatus,
		handshakeStatus: apiBlock?.handshakeStatus ?? fallbackBlock.handshakeStatus ?? DEFAULT_BLOCK_VALUES.handshakeStatus,
		updatedAt: apiBlock?.updatedAt ?? fallbackBlock.updatedAt ?? new Date().toISOString(),
		deleteRequested: apiBlock?.deleteRequested ?? fallbackBlock.deleteRequested ?? DEFAULT_BLOCK_VALUES.deleteRequested
	};
}

// Step2 実動確認用:
// block 不在時は null、存在時は BLOCK_DETAIL_VIEW_MODEL_FIELDS だけを返す
function buildBlockDetailViewModel(block, blockId) {
	if (!block) {
		return null;
	}

	const normalizedBlock = normalizeBlock(block, { id: String(blockId) });

	// Step2 実動確認用: 返却キーを明示して整形確認を追いやすくする
	return {
		id: normalizedBlock.id,
		name: normalizedBlock.name,
		type: normalizedBlock.type,
		status: normalizedBlock.status,
		connectionStatus: normalizedBlock.connectionStatus,
		freezeStatus: normalizedBlock.freezeStatus,
		handshakeStatus: normalizedBlock.handshakeStatus,
		updatedAt: normalizedBlock.updatedAt,
		deleteRequested: normalizedBlock.deleteRequested
	};
}

// Block list/detail retrieval
// API対応先: GET /blocks
export async function getBlocks() {
	// Fallback source: API が使えない場合は常に mock 一覧を返す
	const fallbackBlocks = cloneMockBlocks();

	try {
		// Success path: API 取得結果を UI 互換 shape に正規化して返す
		const response = await getBlocksJson();
		const apiBlocks = resolveBlocksListResponse(response);

		if (!Array.isArray(apiBlocks)) {
			// Fallback path (shape mismatch): API 応答形式が一覧として解釈できない
			return fallbackBlocks;
		}

		const normalizedBlocks = apiBlocks.map((apiBlock) => {
			const fallbackBlock = mockBlocks.find((block) => block.id === String(apiBlock?.id)) ?? {};
			return normalizeBlock(apiBlock, fallbackBlock);
		});

		return normalizedBlocks;
	} catch {
		// Fallback path (request error): API 呼び出し失敗時は mock 一覧へ退避
		return fallbackBlocks;
	}
}

export async function getConnectionManagementItems() {
	const blocks = await getBlocks();
	return blocks.map((block) => ({
		id: block.id,
		name: block.name,
		connectionStatus: block.connectionStatus,
		handshakeStatus: block.handshakeStatus ?? "idle"
	}));
}

// API対応先: GET /blocks/{id}
// 本API呼び出し + fallback 方針: getJson(`/blocks/${blockId}`) に失敗した場合は getBlocks() -> mock へフォールバック。
export async function getBlockById(blockId) {
	const normalizedBlockId = String(blockId);
	// Final fallback candidate: id 一致の mock 単体
	const fallbackMockBlock = mockBlocks.find((item) => item.id === normalizedBlockId) ?? null;

	try {
		// Success path: API 詳細取得
		const response = await getJson(`/blocks/${normalizedBlockId}`);
		const apiBlock = resolveBlockDetailResponse(response);

		if (apiBlock && typeof apiBlock === "object" && !Array.isArray(apiBlock)) {
			return normalizeBlock(apiBlock, fallbackMockBlock ?? {});
		}

		// Fallback path (shape mismatch): 詳細レスポンスが単一 object として解釈できない
	} catch (error) {
		// 404 は block 不存在として null 返却を優先し、UI 側で安全に扱いやすくする
		if (getFailedGetStatus(error) === 404) {
			return null;
		}

		// Fallback path (request error): 一覧経由フォールバックへ
	}

	// Fallback path (list): getBlocks() 経由で同一 id を再探索
	const blocks = await getBlocks();
	const blockFromList = blocks.find((item) => item.id === normalizedBlockId) ?? null;
	if (blockFromList) {
		return { ...blockFromList };
	}

	// Fallback path (mock single) -> not found なら null
	return fallbackMockBlock ? { ...fallbackMockBlock } : null;
}

// Handshake state management
// API対応先: GET /blocks/{id}/handshake
export function getHandshakeStatus(blockId) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		return Promise.resolve(null);
	}

	return Promise.resolve(block.handshakeStatus ?? null);
}

// API対応先: POST /blocks/{id}/handshake
export function setHandshakeStatus(blockId, nextStatus) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		return Promise.resolve({ success: false, message: "Block not found.", block: null });
	}

	const allowedStatuses = new Set(["idle", "pending", "success", "failed"]);
	if (!allowedStatuses.has(nextStatus)) {
		return Promise.resolve({ success: false, message: "Invalid handshake status.", block: { ...block } });
	}

	block.handshakeStatus = nextStatus;
	block.updatedAt = new Date().toISOString();

	return Promise.resolve({
		success: true,
		message: `${block.name} handshake status updated to ${nextStatus}.`,
		block: { ...block }
	});
}

// Detail/dashboard view models
export async function getBlockDetailViewModel(blockId) {
	const block = await getBlockById(blockId);
	// getBlockById の成功/404/fallback 結果を GUI 詳細表示用の shape に整形する
	return buildBlockDetailViewModel(block, blockId);
}

// Step2 実動確認用: ブラウザコンソールから整形結果を即確認する
// 例: await inspectBlockDetailViewModel('block-001')
export async function inspectBlockDetailViewModel(blockId) {
	const vm = await getBlockDetailViewModel(blockId);
	if (vm === null) {
		console.log(`[Step2] getBlockDetailViewModel("${blockId}") => null (block not found)`);
		return null;
	}
	console.log(`[Step2] getBlockDetailViewModel("${blockId}") keys:`, BLOCK_DETAIL_VIEW_MODEL_KEYS);
	console.table(vm);
	return vm;
}

// Connection actions
function buildConnectPath(blockId) {
	return `/blocks/${encodeURIComponent(String(blockId))}/connect`;
}

function resolveConnectResponseBlock(response) {
	if (response?.block && typeof response.block === "object" && !Array.isArray(response.block)) {
		return response.block;
	}

	if (response?.data?.block && typeof response.data.block === "object" && !Array.isArray(response.data.block)) {
		return response.data.block;
	}

	return null;
}

async function finalizeConnectResult(block, blockId, responseMeta = {}) {
	await appendAuditLog({
		action: "connect",
		target: createAuditTarget(block, blockId),
		result: "success",
		operator: "local-user"
	});

	return {
		success: true,
		message: responseMeta.message ?? `${block.name} connected.`,
		block: { ...block },
		source: responseMeta.source ?? "fallback",
		apiSuccess: responseMeta.apiSuccess ?? null,
		apiMessage: responseMeta.apiMessage ?? null
	};
}

function buildDisconnectPath(blockId) {
	return `/blocks/${encodeURIComponent(String(blockId))}/disconnect`;
}

function resolveDisconnectResponseBlock(response) {
	if (response?.block && typeof response.block === "object" && !Array.isArray(response.block)) {
		return response.block;
	}

	if (response?.data?.block && typeof response.data.block === "object" && !Array.isArray(response.data.block)) {
		return response.data.block;
	}

	return null;
}

async function finalizeDisconnectResult(block, blockId, responseMeta = {}) {
	await appendAuditLog({
		action: "disconnect",
		target: createAuditTarget(block, blockId),
		result: "success",
		operator: "local-user"
	});

	return {
		success: true,
		message: responseMeta.message ?? `${block.name} disconnected.`,
		block: { ...block },
		source: responseMeta.source ?? "fallback",
		apiSuccess: responseMeta.apiSuccess ?? null,
		apiMessage: responseMeta.apiMessage ?? null
	};
}

function resolveFreezeResponseBlock(response) {
	if (response?.block && typeof response.block === "object" && !Array.isArray(response.block)) {
		return response.block;
	}

	if (response?.data?.block && typeof response.data.block === "object" && !Array.isArray(response.data.block)) {
		return response.data.block;
	}

	return null;
}

function buildFreezePath(blockId) {
	return `/blocks/${encodeURIComponent(String(blockId))}/freeze`;
}

function buildUnfreezePath(blockId) {
	return `/blocks/${encodeURIComponent(String(blockId))}/unfreeze`;
}

async function finalizeFreezeResult(block, blockId, message) {
	await appendAuditLog({
		action: "freeze",
		target: createAuditTarget(block, blockId),
		result: "success",
		operator: "local-user"
	});

	return {
		success: true,
		message,
		block: { ...block }
	};
}

function resolveUnfreezeResponseBlock(response) {
	if (response?.block && typeof response.block === "object" && !Array.isArray(response.block)) {
		return response.block;
	}

	if (response?.data?.block && typeof response.data.block === "object" && !Array.isArray(response.data.block)) {
		return response.data.block;
	}

	return null;
}

function buildExportPath(blockId) {
	return `/blocks/${encodeURIComponent(String(blockId))}/export`;
}

function resolveExportResponseBlock(response) {
	if (response?.block && typeof response.block === "object" && !Array.isArray(response.block)) {
		return response.block;
	}

	if (response?.data?.block && typeof response.data.block === "object" && !Array.isArray(response.data.block)) {
		return response.data.block;
	}

	return null;
}

async function finalizeUnfreezeResult(block, blockId, message) {
	await appendAuditLog({
		action: "unfreeze",
		target: createAuditTarget(block, blockId),
		result: "success",
		operator: "local-user"
	});

	return {
		success: true,
		message,
		block: { ...block }
	};
}

// API対応先: POST /blocks/{id}/connect
export async function connectBlock(blockId) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		return Promise.resolve({ success: false, message: "Block not found.", block: null });
	}

	if (block.connectionStatus === "connected") {
		return Promise.resolve({
			success: true,
			message: `${block.name} is already connected.`,
			block: { ...block },
			source: "local",
			apiSuccess: null,
			apiMessage: null
		});
	}

	const connectPath = buildConnectPath(blockId);

	try {
		// API success path: success=true の場合は API 応答を優先しつつ mock も同期する
		const response = await postJson(connectPath);

		if (response?.success === true) {
			const apiBlock = resolveConnectResponseBlock(response);
			const normalizedBlock = normalizeBlock(
				{
					...apiBlock,
					connectionStatus: apiBlock?.connectionStatus ?? "connected"
				},
				block
			);

			Object.assign(block, normalizedBlock);
			return finalizeConnectResult(block, blockId, {
				message: response?.message ?? `${block.name} connected.`,
				source: "api",
				apiSuccess: true,
				apiMessage: response?.message ?? null
			});
		}

		// API failure path: UI を壊さないため既存 mock 更新へ fallback する
	} catch (error) {
		block.connectionStatus = "connected";
		block.updatedAt = new Date().toISOString();
		return finalizeConnectResult(block, blockId, {
			message: `${block.name} connected.`,
			source: "fallback",
			apiSuccess: false,
			apiMessage: String(error?.message ?? "POST connect failed.")
		});
	}

	block.connectionStatus = "connected";
	block.updatedAt = new Date().toISOString();
	return finalizeConnectResult(block, blockId, {
		message: `${block.name} connected.`,
		source: "fallback",
		apiSuccess: false,
		apiMessage: "API returned success=false or unexpected response."
	});
}

// API対応先: POST /blocks/{id}/disconnect
export async function disconnectBlock(blockId) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		return Promise.resolve({ success: false, message: "Block not found.", block: null });
	}

	if (block.connectionStatus === "disconnected") {
		return Promise.resolve({
			success: true,
			message: `${block.name} is already disconnected.`,
			block: { ...block },
			source: "local",
			apiSuccess: null,
			apiMessage: null
		});
	}

	const disconnectPath = buildDisconnectPath(blockId);

	try {
		// API success path: success=true の場合は API 応答を優先しつつ mock も同期する
		const response = await postJson(disconnectPath);

		if (response?.success === true) {
			const apiBlock = resolveDisconnectResponseBlock(response);
			const normalizedBlock = normalizeBlock(
				{
					...apiBlock,
					connectionStatus: apiBlock?.connectionStatus ?? "disconnected"
				},
				block
			);

			Object.assign(block, normalizedBlock);
			return finalizeDisconnectResult(block, blockId, {
				message: response?.message ?? `${block.name} disconnected.`,
				source: "api",
				apiSuccess: true,
				apiMessage: response?.message ?? null
			});
		}

		// API failure path: UI を壊さないため既存 mock 更新へ fallback する
	} catch (error) {
		block.connectionStatus = "disconnected";
		block.updatedAt = new Date().toISOString();
		return finalizeDisconnectResult(block, blockId, {
			message: `${block.name} disconnected.`,
			source: "fallback",
			apiSuccess: false,
			apiMessage: String(error?.message ?? "POST disconnect failed.")
		});
	}

	block.connectionStatus = "disconnected";
	block.updatedAt = new Date().toISOString();
	return finalizeDisconnectResult(block, blockId, {
		message: `${block.name} disconnected.`,
		source: "fallback",
		apiSuccess: false,
		apiMessage: "API returned success=false or unexpected response."
	});
}

// Freeze actions
// API対応先: POST /blocks/{id}/freeze
export async function freezeBlock(blockId) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		// fail-safe: blockId 未一致 -> 呼び出し元で success:false を確認できる
		return Promise.resolve({ success: false, message: "Block not found.", block: null });
	}

	try {
		// [成功系] postJson -> response.success === true -> API 戻り値を優先して freezeStatus 更新
		const response = await postJson(buildFreezePath(blockId), {});

		if (response?.success === true) {
			const apiBlock = resolveFreezeResponseBlock(response);
			const normalizedBlock = normalizeBlock(
				{
					...apiBlock,
					// API 戻り値に freezeStatus がなければ "frozen" を補填
					freezeStatus: apiBlock?.freezeStatus ?? "frozen"
				},
				block
			);

			Object.assign(block, normalizedBlock);
			return finalizeFreezeResult(block, blockId, response?.message ?? `${block.name} frozen.`);
		}
		// [失敗系] response.success !== true -> catch せず fallback へ落とす
	} catch {
		// [失敗系] fetch 例外 (4xx/5xx/network) -> fallback へ落とす
	}

	// [fallback] API 失敗/shape 不一致 -> mock を直接更新して success:true を返す
	block.freezeStatus = "frozen";
	block.updatedAt = new Date().toISOString();
	return finalizeFreezeResult(block, blockId, `${block.name} frozen.`);
}

// API対応先: POST /blocks/{id}/unfreeze
export async function unfreezeBlock(blockId) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		// fail-safe: blockId 未一致 -> 呼び出し元で success:false を確認できる
		return Promise.resolve({ success: false, message: "Block not found.", block: null });
	}

	try {
		// [成功系] postJson -> response.success === true -> API 戻り値を優先して freezeStatus 更新
		const response = await postJson(buildUnfreezePath(blockId), {});

		if (response?.success === true) {
			const apiBlock = resolveUnfreezeResponseBlock(response);
			const normalizedBlock = normalizeBlock(
				{
					...apiBlock,
					// API 戻り値に freezeStatus がなければ "active" を補填
					freezeStatus: apiBlock?.freezeStatus ?? "active"
				},
				block
			);

			Object.assign(block, normalizedBlock);
			return finalizeUnfreezeResult(block, blockId, response?.message ?? `${block.name} unfrozen.`);
		}
		// [失敗系] response.success !== true -> catch せず fallback へ落とす
	} catch {
		// [失敗系] fetch 例外 (4xx/5xx/network) -> fallback へ落とす
	}

	// [fallback] API 失敗/shape 不一致 -> mock を直接更新して success:true を返す
	block.freezeStatus = "active";
	block.updatedAt = new Date().toISOString();
	return finalizeUnfreezeResult(block, blockId, `${block.name} unfrozen.`);
}

// Freeze warning metadata for freeze/unfreeze UI flow
export function getFreezeDangerMeta(blockId, actionType) {
	const normalizedActionType = actionType === "unfreeze" ? "unfreeze" : "freeze";
	const block = mockBlocks.find((item) => item.id === String(blockId)) ?? null;

	if (!block) {
		return null;
	}

	const title = normalizedActionType === "freeze"
		? "Freeze 実行前の警告"
		: "Unfreeze 実行前の警告";

	const message = normalizedActionType === "freeze"
		? "Freeze は対象 Block の処理を停止または制限する可能性があります。影響範囲を確認してください。"
		: "Unfreeze は対象 Block の処理再開により負荷変動を引き起こす可能性があります。影響範囲を確認してください。";

	return {
		actionType: normalizedActionType,
		title,
		message,
		blockName: block.name,
		requiresConfirmation: true
	};
}

// LockGuard metadata for export/delete UI flow
export function getLockGuardMeta(blockId, actionType) {
	const normalizedActionType = actionType === "delete" ? "delete" : "export";
	const block = mockBlocks.find((item) => item.id === String(blockId)) ?? null;

	if (!block) {
		return null;
	}

	const isDelete = normalizedActionType === "delete";
	const title = isDelete ? "Delete 実行前の警告" : "Export 実行前の警告";
	const message = isDelete
		? "Delete は対象 Block の復旧を困難にする可能性があります。実行前に影響範囲を確認してください。"
		: "Export は対象 Block の機密情報を含む可能性があります。実行前に出力先と取り扱いを確認してください。";
	const confirmationText = isDelete
		? mockAuthConfig.deleteConfirmationText
		: mockAuthConfig.exportConfirmationText;

	return {
		actionType: normalizedActionType,
		title,
		message,
		blockName: block.name,
		confirmationText,
		requiresPassword: true,
		requiresTwoFactor: true,
		requiresFinalCheck: true
	};
}

// LockGuard actions (export/delete) with auth checks
// API対応先: POST /blocks/{id}/export
export async function exportBlock(blockId, authInfo) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		await appendAuditLog({
			action: "export",
			target: String(blockId),
			result: "failed",
			operator: authInfo?.operator ?? "local-user"
		});
		return { success: false, message: "Block not found.", block: null };
	}

	if (!hasCompletedAuth(authInfo, "export")) {
		const message = getAuthFailureMessage(authInfo, "export");
		await appendAuditLog({
			action: "export",
			target: createAuditTarget(block, blockId),
			result: "failed",
			operator: authInfo?.operator ?? "local-user"
		});
		return { success: false, message, block: { ...block } };
	}

	const exportPath = buildExportPath(blockId);

	try {
		// API success path: postJson(`/blocks/${blockId}/export`, authInfo) を優先
		const response = await postJson(exportPath, authInfo ?? {});

		if (response?.success === true) {
			const apiBlock = resolveExportResponseBlock(response);
			if (apiBlock) {
				const normalizedBlock = normalizeBlock(apiBlock, block);
				Object.assign(block, normalizedBlock);
			}

			await appendAuditLog({
				action: "export",
				target: createAuditTarget(block, blockId),
				result: "success",
				operator: authInfo?.operator ?? "local-user"
			});

			return {
				success: true,
				message: response?.message ?? `${block.name} export queued.`,
				block: { ...block }
			};
		}
	} catch {
		// API failure path: 既存 mock 処理にフォールバック
	}

	await appendAuditLog({
		action: "export",
		target: createAuditTarget(block, blockId),
		result: "success",
		operator: authInfo?.operator ?? "local-user"
	});

	return { success: true, message: `${block.name} export queued.`, block: { ...block } };
}


// API対応先: DELETE /blocks/{id}（互換時: POST /blocks/{id}/delete）
export async function deleteBlock(blockId, authInfo) {
	const block = mockBlocks.find((item) => item.id === String(blockId));
	if (!block) {
		await appendAuditLog({
			action: "delete",
			target: String(blockId),
			result: "failed",
			operator: authInfo?.operator ?? "local-user"
		});
		return { success: false, message: "Block not found.", block: null };
	}

	if (!hasCompletedAuth(authInfo, "delete")) {
		const message = getAuthFailureMessage(authInfo, "delete");
		await appendAuditLog({
			action: "delete",
			target: createAuditTarget(block, blockId),
			result: "failed",
			operator: authInfo?.operator ?? "local-user"
		});
		return { success: false, message, block: { ...block } };
	}

	block.deleteRequested = true;
	block.updatedAt = new Date().toISOString();

	await appendAuditLog({
		action: "delete",
		target: createAuditTarget(block, blockId),
		result: "success",
		operator: authInfo?.operator ?? "local-user"
	});

	return { success: true, message: `${block.name} delete queued.`, block: { ...block } };
}

// Dashboard aggregation
export async function getBlockDashboardStats() {
	const blocks = await getBlocks();

	return {
		totalBlocks: blocks.length,
		connectedBlocks: blocks.filter((block) => block.connectionStatus === "connected").length,
		disconnectedBlocks: blocks.filter((block) => block.connectionStatus === "disconnected").length,
		frozenBlocks: blocks.filter((block) => block.freezeStatus === "frozen").length,
		activeBlocks: blocks.filter((block) => block.freezeStatus === "active").length,
		deleteRequestedBlocks: blocks.filter((block) => block.deleteRequested === true).length
	};
}
