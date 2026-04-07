
import { connectBlock, deleteBlock, disconnectBlock, exportBlock, freezeBlock, getBlockById, getBlockDashboardStats, getBlockDetailViewModel, getBlocks, getConnectionManagementItems, getFreezeDangerMeta, getLockGuardMeta, setHandshakeStatus, unfreezeBlock } from "./services/blockService.js";
import * as logService from "./services/logService.js";

(() => {
  // Service boundary: switch this map when replacing mock services with API-backed services.
  const services = {
    block: {
      getBlocks,
      getBlockById,
      getConnectionManagementItems,
      getBlockDetailViewModel,
      getBlockDashboardStats,
      getFreezeDangerMeta,
      getLockGuardMeta,
      setHandshakeStatus,
      connectBlock,
      disconnectBlock,
      freezeBlock,
      unfreezeBlock,
      exportBlock,
      deleteBlock
    },
    log: {
      getAuditLogs: (...args) => logService.getAuditLogs(...args),
      getAuditLogViewItems: (...args) => logService.getAuditLogViewItems(...args),
      getAuditLogCount: (...args) => logService.getAuditLogCount(...args),
      getSecuritySettings: (...args) => logService.getSecuritySettings(...args),
      updateSecuritySettings: (...args) => logService.updateSecuritySettings(...args),
      getRecentAuditLogs: (...args) => logService.getRecentAuditLogs?.(...args)
    }
  };

  // script.js -> service boundary
  // 描画系・一覧取得系・危険操作系・settings系・audit系の入口をここへ集約する。

  const statusChipClass = {
    running: 'is-ok',
    warning: 'is-danger',
    stopped: 'is-warn'
  };
  const statusLabel = {
    running: '稼働中',
    warning: '要確認',
    stopped: '停止中'
  };
  const connectionChipClass = {
    connected: 'is-connected',
    disconnected: 'is-disconnected'
  };
  const connectionLabel = {
    connected: 'Connected',
    disconnected: 'Disconnected'
  };
  const freezeChipClass = {
    active: 'is-ok',
    frozen: 'is-warn'
  };
  const freezeLabel = {
    active: 'Active',
    frozen: 'Frozen'
  };
  const uiText = {
    blockDetailEmpty: 'Block が選択されていません',
    blockDetailSelected: '選択中の Block 詳細',
    freezeWarningInitialTitle: 'Freeze / Unfreeze 実行前の確認',
    freezeWarningInitialMessage: '対象 Block を選択すると、操作前の確認事項を表示します。',
    freezeWarningEmptyBlockName: '未選択',
    freezeWarningMissingTitle: '警告情報を表示できません',
    freezeWarningMissingMessage: '対象 Block が見つかりません。',
    lockGuardEmptyBlockName: '未選択',
    lockGuardEmptyActionType: '未選択',
    lockGuardUnavailableMessage: '対象 Block が見つかりません。',
    settingsLoading: '設定値を読み込み中です',
    settingsReady: '現在の設定値を表示しています',
    settingsUnavailable: '設定値を表示できません',
    dashboardRecentLogEmpty: '表示できるログはありません',
    dashboardAuditEmpty: '監査ログはありません',
    filteredAuditEmpty: '条件に一致する監査ログはありません',
    tableEmpty: '表示できるデータはありません',
    connectionManagementEmpty: '表示できる接続情報はありません',
    handshakeStatusDefault: '未取得',
    freezeWarningMissingBlockName: '-',
    lockGuardActionLabelDelete: 'Delete',
    lockGuardActionLabelExport: 'Export',
    msgConfirmRequired: '確認チェックを有効にしてから実行してください。',
    msgLockGuardInvalidState: 'LockGuard の表示状態が不正です。再度開いて実行してください。',
    msgLockGuardMissingTarget: 'Export / Delete の対象情報がありません。',
    msgLockGuardFailed: 'Export / Delete の実行に失敗しました。',
    msgLockGuardOpened: 'LockGuard を表示しました。',
    msgLockGuardOpenFailed: 'LockGuard 情報を表示できませんでした。',
    msgFreezeMissingTarget: 'Freeze / Unfreeze の対象情報がありません。',
    msgFreezeFailed: 'Freeze / Unfreeze の実行に失敗しました。',
    msgFreezeWarningShown: 'Freeze / Unfreeze 実行前の警告を表示しました。',
    msgFreezeWarningShowFailed: '警告情報を表示できませんでした。',
    msgBlockActionFailed: 'Block 操作の実行に失敗しました。',
    msgBlockListLoadFailed: 'Block 一覧の取得に失敗しました。',
    msgBlockDetailLoadFailed: 'Block 詳細の取得に失敗しました。',
    msgSettingsLoadFailed: 'Settings の取得に失敗しました。',
    msgSettingsSaveFailed: 'Settings の保存に失敗しました。',
    msgSettingsSaved: 'Settings を保存しました。',
    msgAuditLogLoadFailed: 'Audit Log の取得に失敗しました。'
  };
  const handshakeChipClass = {
    idle: 'is-warn',
    pending: 'is-warn',
    success: 'is-ok',
    failed: 'is-danger'
  };
  const pendingBlockActions = new Set();
  const domRefs = {
    // === ページコンテナ (data-page) ===
    dashboardPage:          document.getElementById('page-dashboard'),
    blocksPage:             document.getElementById('page-blocks'),
    connectionsPage:        document.getElementById('page-connections'),
    exportDeletePage:       document.getElementById('page-export-delete'),
    auditPage:              document.getElementById('page-audit'),
    settingsPage:           document.getElementById('page-settings'),
    // === ヘッダー / メッセージ表示領域 ===
    topbarTitle:            document.getElementById('topbar-title'),
    operationMessage:       document.getElementById('block-operation-message'),
    // === Dashboard (Block一覧・集計) ===
    dashboardBlockListSection:  document.getElementById('dashboard-block-list-section'),
    dashboardBlocksBody:        document.getElementById('dashboard-blocks-body'),
    dashboardAuditLogBody:      document.getElementById('dashboard-audit-log-body'),
    dashboardRecentLog:         document.getElementById('recentLog'),
    // === Block 詳細 — Dashboard 内 (id prefix: dashboard-detail-*) ===
    dashboardBlockDetailPanel:       document.getElementById('dashboard-block-detail-panel'),
    dashboardBlockDetailPlaceholder: document.getElementById('dashboard-block-detail-placeholder'),
    dashboardDetailHandshakeStatus:  document.getElementById('dashboard-detail-handshakeStatus'),
    // === Block 詳細 — Block管理ページ (id prefix: detail-*) ===
    blockDetailPanel:           document.getElementById('block-detail'),
    blockDetailPlaceholder:     document.getElementById('block-detail-placeholder'),
    blockDetailHandshakeStatus: document.getElementById('detail-handshakeStatus'),
    // === Freeze/Unfreeze 警告 ===
    freezeWarningSection:   document.getElementById('freeze-warning'),
    freezeWarningTitle:     document.getElementById('freeze-warning-title'),
    freezeWarningMessage:   document.getElementById('freeze-warning-message'),
    freezeWarningBlockName: document.getElementById('freeze-warning-block-name'),
    freezeWarningConfirm:   document.getElementById('freeze-warning-confirm'),
    freezeWarningExecute:   document.getElementById('freeze-warning-execute'),
    freezeWarningCancel:    document.getElementById('freeze-warning-cancel'),
    // === LockGuard ===
    lockGuardPanel:              document.getElementById('lockguard-panel'),
    lockGuardTitle:              document.getElementById('lockguard-title'),
    lockGuardDangerDescription:  document.getElementById('lockguard-danger-description'),
    lockGuardTargetBlock:        document.getElementById('lockguard-target-block'),
    lockGuardActionType:         document.getElementById('lockguard-action-type'),
    lockGuardPassword:           document.getElementById('lockguard-password'),
    lockGuardTwoFactorCode:      document.getElementById('lockguard-2fa-code'),
    lockGuardConfirmationText:   document.getElementById('lockguard-confirmation-text'),
    lockGuardConfirmed:          document.getElementById('lockguard-final-confirm'),
    lockGuardExecuteButton:      document.getElementById('lockguard-execute-button'),
    // === 接続/切断管理 ===
    connectionManagementPanel: document.getElementById('connection-management-panel'),
    connectionManagementList:  document.getElementById('connection-management-list'),
    // === Audit Log ===
    auditLogPage:         document.getElementById('audit-log-page'),
    auditLogListBody:     document.getElementById('audit-log-list-body'),
    auditLogCount:        document.getElementById('audit-log-count'),
    auditLogFilterAction: document.getElementById('audit-log-filter-action'),
    auditLogFilterResult: document.getElementById('audit-log-filter-result'),
    // === Security / Settings ===
    securitySettingsPanel:    document.getElementById('settings-panel'),
    settingsPanelPlaceholder: document.getElementById('settings-panel-placeholder'),
    settingsSaveButton:       document.getElementById('settings-save-button'),
    // === Block 一覧 tbody (各ページ) ===
    blocksTableBody:      document.getElementById('blocks-table-body'),
    exportDeleteTableBody: document.getElementById('exportdel-table-body')
  };

  const operationMessage = domRefs.operationMessage;
  let lastOperationMessage = '';
  let lastOperationMessageSuccess = true;
  const freezeWarningSection = domRefs.freezeWarningSection;
  const freezeWarningTitle = domRefs.freezeWarningTitle;
  const freezeWarningMessage = domRefs.freezeWarningMessage;
  const freezeWarningBlockName = domRefs.freezeWarningBlockName;
  const freezeWarningConfirm = domRefs.freezeWarningConfirm;
  const freezeWarningExecute = domRefs.freezeWarningExecute;
  const freezeWarningCancel = domRefs.freezeWarningCancel;
  const lockGuardPanel = domRefs.lockGuardPanel;
  const lockGuardTitle = domRefs.lockGuardTitle;
  const lockGuardDangerDescription = domRefs.lockGuardDangerDescription;
  const lockGuardTargetBlock = domRefs.lockGuardTargetBlock;
  const lockGuardActionType = domRefs.lockGuardActionType;
  const lockGuardPassword = domRefs.lockGuardPassword;
  const lockGuardTwoFactorCode = domRefs.lockGuardTwoFactorCode;
  const lockGuardConfirmationText = domRefs.lockGuardConfirmationText;
  const lockGuardConfirmed = domRefs.lockGuardConfirmed;
  const lockGuardExecuteButton = domRefs.lockGuardExecuteButton;
  let selectedBlockId = null;
  let blockDetailRequestSeq = 0;
  const lockGuardDefaultTitle = lockGuardTitle?.textContent ?? 'LockGuard';
  const lockGuardDefaultDescription = lockGuardDangerDescription?.textContent ?? 'Export / Delete は危険操作です。実行前に再認証と最終確認が必要です。';
  const lockGuardDefaultConfirmationPlaceholder = lockGuardConfirmationText?.getAttribute('placeholder') ?? 'EXPORT または DELETE を入力';
  const auditLogCount = domRefs.auditLogCount;
  const auditLogFilterAction = domRefs.auditLogFilterAction;
  const auditLogFilterResult = domRefs.auditLogFilterResult;

  const detailFieldKeys = [
    'id',
    'name',
    'type',
    'status',
    'connectionStatus',
    'freezeStatus',
    'handshakeStatus',
    'updatedAt',
    'deleteRequested'
  ];

  const setDashboardValue = (id, value) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.textContent = value ?? '-';
  };

  const formatTableDateTime = (value) => {
    if (typeof value !== 'string' || value.length === 0) return '-';
    return value.replace('T', ' ').slice(0, 16);
  };

  const normalizeSelectedBlockId = (blockId) => {
    if (blockId == null) return null;
    const normalized = String(blockId).trim();
    return normalized.length > 0 ? normalized : null;
  };

  const setSelectedBlockId = (blockId) => {
    selectedBlockId = normalizeSelectedBlockId(blockId);
    return selectedBlockId;
  };

  const normalizeBlockListForView = (blocks) => {
    if (!Array.isArray(blocks)) return [];

    return blocks
      .filter((block) => block && typeof block === 'object')
      .map((block) => ({
        id: String(block.id ?? ''),
        name: block.name ?? '-',
        type: block.type ?? '-',
        status: block.status ?? 'stopped',
        connectionStatus: block.connectionStatus ?? 'disconnected',
        freezeStatus: block.freezeStatus ?? 'active',
        updatedAt: block.updatedAt ?? ''
      }));
  };

  const normalizeDangerActionType = (actionType, fallback = '') => {
    if (actionType === 'freeze' || actionType === 'unfreeze' || actionType === 'export' || actionType === 'delete') {
      return actionType;
    }
    return fallback;
  };

  const setFreezeWarningState = ({ blockId = '', actionType = '' } = {}) => {
    if (!freezeWarningSection) return;
    freezeWarningSection.dataset.warningBlockId = String(blockId ?? '');
    freezeWarningSection.dataset.warningType = normalizeDangerActionType(actionType);
  };

  const getFreezeWarningState = () => ({
    blockId: freezeWarningSection?.dataset.warningBlockId ?? '',
    actionType: normalizeDangerActionType(freezeWarningSection?.dataset.warningType)
  });

  const setLockGuardState = ({ state = 'placeholder', blockId = '', actionType = '' } = {}) => {
    if (!lockGuardPanel) return;
    lockGuardPanel.dataset.lockguardState = state;
    lockGuardPanel.dataset.blockId = String(blockId ?? '');
    lockGuardPanel.dataset.actionType = normalizeDangerActionType(actionType, 'export');
  };

  const getLockGuardState = () => ({
    state: lockGuardPanel?.dataset.lockguardState ?? 'placeholder',
    blockId: lockGuardPanel?.dataset.blockId ?? '',
    actionType: normalizeDangerActionType(lockGuardPanel?.dataset.actionType)
  });

  const showOperationMessage = (message, isSuccess = true) => {
    lastOperationMessage = message ?? '';
    lastOperationMessageSuccess = isSuccess !== false;
    if (!operationMessage) return;
    operationMessage.textContent = message ?? '';
    operationMessage.hidden = !message;
    operationMessage.style.color = isSuccess ? '#d9f99d' : '#fca5a5';
    operationMessage.style.borderColor = isSuccess ? 'rgba(163, 230, 53, 0.28)' : 'rgba(248, 113, 113, 0.32)';
    operationMessage.style.background = isSuccess ? 'rgba(20, 83, 45, 0.22)' : 'rgba(127, 29, 29, 0.22)';
  };

  // Shared message mapping for service call results (no behavior change)
  const showServiceResultMessage = (result) => {
    showOperationMessage(result?.message ?? '', result?.success !== false);
  };

    // Shared service result normalization for future API envelopes.
    // Expected keys: success / message / block / list / settings / data
    const resolveServiceResult = (result, preferredKeys = []) => {
      const isObject = Boolean(result) && typeof result === 'object' && !Array.isArray(result);
      const isEnvelope = isObject && (
        'success' in result ||
        'message' in result ||
        'list' in result ||
        'block' in result ||
        'settings' in result ||
        'data' in result
      );

      if (!isEnvelope) {
        return { success: true, message: '', data: result };
      }

      const dataKey = [...preferredKeys, 'list', 'block', 'settings', 'data']
        .find((key) => Object.prototype.hasOwnProperty.call(result, key));

      return {
        success: result.success !== false,
        message: typeof result.message === 'string' ? result.message : '',
        data: dataKey ? result[dataKey] : null
      };
    };

    const loadServiceData = async (loader, { preferredKeys = [], failureMessage = '' } = {}) => {
      try {
        const result = await loader();
        const normalized = resolveServiceResult(result, preferredKeys);

        if (normalized.success === false) {
          // fail-safe: service が success=false を返した場合は message のみ更新して描画側に中断を伝える
          showOperationMessage(normalized.message || failureMessage, false);
          return { ok: false, data: null };
        }

        return { ok: true, data: normalized.data };
      } catch {
        // fail-safe: 例外時も message のみ更新して描画側に中断を伝える
        showOperationMessage(failureMessage, false);
        return { ok: false, data: null };
      }
    };

  const serviceQueries = {
    // 描画系 / 一覧取得系
    getBlockDashboardStats: () => loadServiceData(
      () => services.block.getBlockDashboardStats(),
      { preferredKeys: ['stats', 'data'], failureMessage: uiText.msgBlockListLoadFailed }
    ),
    getBlocks: () => loadServiceData(
      () => services.block.getBlocks(),
      { preferredKeys: ['list', 'blocks'], failureMessage: uiText.msgBlockListLoadFailed }
    ),
    getConnectionManagementItems: () => loadServiceData(
      () => services.block.getConnectionManagementItems(),
      { preferredKeys: ['list', 'items'], failureMessage: uiText.msgBlockListLoadFailed }
    ),
    getBlockDetailViewModel: (blockId) => loadServiceData(
      async () => {
        if (typeof services.block.getBlockDetailViewModel === 'function') {
          return services.block.getBlockDetailViewModel(blockId);
        }

        if (typeof services.block.getBlockById === 'function') {
          return services.block.getBlockById(blockId);
        }

        return null;
      },
      { preferredKeys: ['block', 'detail', 'data'], failureMessage: uiText.msgBlockDetailLoadFailed }
    ),

    // Settings 系
    getSecuritySettings: () => (typeof services.log.getSecuritySettings === 'function'
      ? loadServiceData(
        () => services.log.getSecuritySettings(),
        { preferredKeys: ['settings', 'data'], failureMessage: uiText.msgSettingsLoadFailed }
      )
      : Promise.resolve({ ok: true, data: null })),
    updateSecuritySettings: (nextSettings) => (typeof services.log.updateSecuritySettings === 'function'
      ? loadServiceData(
        () => services.log.updateSecuritySettings(nextSettings),
        { preferredKeys: ['settings', 'data'], failureMessage: uiText.msgSettingsSaveFailed }
      )
      : Promise.resolve({ ok: false, data: null })),

    // Audit 系
    getAuditLogs: () => loadServiceData(
      () => services.log.getAuditLogs(),
      { preferredKeys: ['list', 'logs'], failureMessage: uiText.msgAuditLogLoadFailed }
    ),
    getAuditLogViewItems: (filter) => loadServiceData(
      () => services.log.getAuditLogViewItems(filter),
      { preferredKeys: ['list', 'items'], failureMessage: uiText.msgAuditLogLoadFailed }
    ),
    getAuditLogCount: (filter) => loadServiceData(
      () => services.log.getAuditLogCount(filter),
      { preferredKeys: ['count', 'total', 'value', 'data'], failureMessage: uiText.msgAuditLogLoadFailed }
    ),
    getRecentAuditLogs: (limit = 5) => (typeof services.log.getRecentAuditLogs === 'function'
      ? loadServiceData(
        () => services.log.getRecentAuditLogs(limit),
        { preferredKeys: ['list', 'logs', 'items'], failureMessage: uiText.msgAuditLogLoadFailed }
      )
      : loadServiceData(
        () => services.log.getAuditLogs(),
        { preferredKeys: ['list', 'logs'], failureMessage: uiText.msgAuditLogLoadFailed }
      ))
  };

  const serviceCommands = {
    // Freeze warning導線
    getFreezeDangerMeta: (blockId, actionType) => services.block.getFreezeDangerMeta(blockId, actionType),
    freezeBlock: (blockId) => services.block.freezeBlock(blockId),
    unfreezeBlock: (blockId) => services.block.unfreezeBlock(blockId),

    // LockGuard導線
    getLockGuardMeta: (blockId, actionType) => services.block.getLockGuardMeta(blockId, actionType),
    exportBlock: (blockId, authInfo) => services.block.exportBlock(blockId, authInfo),
    deleteBlock: (blockId, authInfo) => services.block.deleteBlock(blockId, authInfo),

    // 接続/切断・handshake 導線
    connectBlock: (blockId) => services.block.connectBlock(blockId),
    disconnectBlock: (blockId) => services.block.disconnectBlock(blockId),
    setHandshakeStatus: (blockId, status) => services.block.setHandshakeStatus(blockId, status)
  };

  // ---- Freeze warning / LockGuard operation section ----
  // Freeze warning: getFreezeDangerMeta / freezeBlock / unfreezeBlock
  // LockGuard: getLockGuardMeta / exportBlock / deleteBlock

  const renderFreezeWarning = (blockId, actionType) => {
    if (!freezeWarningSection) return false;

    const freezeWarningMeta = serviceCommands.getFreezeDangerMeta(blockId, actionType);
    if (!freezeWarningMeta) {
      freezeWarningSection.hidden = false;
      setFreezeWarningState({ blockId, actionType });
      if (freezeWarningTitle) freezeWarningTitle.textContent = uiText.freezeWarningMissingTitle;
      if (freezeWarningMessage) freezeWarningMessage.textContent = uiText.freezeWarningMissingMessage;
      if (freezeWarningBlockName) freezeWarningBlockName.textContent = uiText.freezeWarningMissingBlockName;
      if (freezeWarningConfirm) freezeWarningConfirm.checked = false;
      return false;
    }

    freezeWarningSection.hidden = false;
    setFreezeWarningState({ blockId, actionType: freezeWarningMeta.actionType });
    if (freezeWarningTitle) freezeWarningTitle.textContent = freezeWarningMeta.title;
    if (freezeWarningMessage) freezeWarningMessage.textContent = freezeWarningMeta.message;
    if (freezeWarningBlockName) freezeWarningBlockName.textContent = freezeWarningMeta.blockName ?? '-';
    if (freezeWarningConfirm) freezeWarningConfirm.checked = false;
    return true;
  };

  const resetFreezeWarning = () => {
    if (!freezeWarningSection) return;
    freezeWarningSection.hidden = true;
    setFreezeWarningState();
    if (freezeWarningConfirm) freezeWarningConfirm.checked = false;
    if (freezeWarningTitle) freezeWarningTitle.textContent = uiText.freezeWarningInitialTitle;
    if (freezeWarningMessage) freezeWarningMessage.textContent = uiText.freezeWarningInitialMessage;
    if (freezeWarningBlockName) freezeWarningBlockName.textContent = uiText.freezeWarningEmptyBlockName;
  };

  const setLockGuardExecuteButtonStyle = (actionType) => {
    if (!lockGuardExecuteButton) return;
    lockGuardExecuteButton.classList.remove('is-export', 'is-delete');
    lockGuardExecuteButton.classList.add(actionType === 'delete' ? 'is-delete' : 'is-export');
  };

  const getLockGuardAuthInfo = () => ({
    password: lockGuardPassword?.value ?? '',
    twoFactorCode: lockGuardTwoFactorCode?.value ?? '',
    confirmationText: lockGuardConfirmationText?.value ?? '',
    confirmed: Boolean(lockGuardConfirmed?.checked)
  });

  const resetLockGuard = () => {
    if (!lockGuardPanel) return;
    lockGuardPanel.hidden = true;
    setLockGuardState({ state: 'placeholder', actionType: 'export' });

    if (lockGuardTitle) lockGuardTitle.textContent = lockGuardDefaultTitle;
    if (lockGuardDangerDescription) lockGuardDangerDescription.textContent = lockGuardDefaultDescription;
    if (lockGuardTargetBlock) lockGuardTargetBlock.textContent = uiText.lockGuardEmptyBlockName;
    if (lockGuardActionType) lockGuardActionType.textContent = uiText.lockGuardEmptyActionType;
    if (lockGuardPassword) lockGuardPassword.value = '';
    if (lockGuardTwoFactorCode) lockGuardTwoFactorCode.value = '';
    if (lockGuardConfirmationText) {
      lockGuardConfirmationText.value = '';
      lockGuardConfirmationText.placeholder = lockGuardDefaultConfirmationPlaceholder;
    }
    if (lockGuardConfirmed) lockGuardConfirmed.checked = false;
    setLockGuardExecuteButtonStyle('delete');
  };

  const renderLockGuard = (blockId, actionType) => {
    if (!lockGuardPanel) return false;

    const lockGuardMeta = serviceCommands.getLockGuardMeta(blockId, actionType);
    const normalizedActionType = lockGuardMeta?.actionType ?? (actionType === 'delete' ? 'delete' : 'export');

    lockGuardPanel.hidden = false;
    setLockGuardState({
      state: lockGuardMeta ? 'ready' : 'missing',
      blockId,
      actionType: normalizedActionType
    });

    if (lockGuardTitle) lockGuardTitle.textContent = lockGuardMeta?.title ?? lockGuardDefaultTitle;
    if (lockGuardDangerDescription) {
      lockGuardDangerDescription.textContent = lockGuardMeta?.message ?? uiText.lockGuardUnavailableMessage;
    }
    if (lockGuardTargetBlock) lockGuardTargetBlock.textContent = lockGuardMeta?.blockName ?? '-';
    if (lockGuardActionType) lockGuardActionType.textContent = normalizedActionType === 'delete' ? uiText.lockGuardActionLabelDelete : uiText.lockGuardActionLabelExport;

    if (lockGuardPassword) lockGuardPassword.value = '';
    if (lockGuardTwoFactorCode) lockGuardTwoFactorCode.value = '';
    if (lockGuardConfirmationText) {
      lockGuardConfirmationText.value = '';
      lockGuardConfirmationText.placeholder = lockGuardMeta?.confirmationText ?? lockGuardDefaultConfirmationPlaceholder;
    }
    if (lockGuardConfirmed) lockGuardConfirmed.checked = false;

    setLockGuardExecuteButtonStyle(normalizedActionType);
    return Boolean(lockGuardMeta);
  };

  // Step6 通し確認フロー (LockGuard 表示 → 入力 → 確認 → 実行 → 再描画):
  //   1. [data-lockguard-open] ボタン -> renderLockGuard(blockId, actionType)  -> state=ready
  //   2. ユーザー入力: password / twoFactorCode / confirmationText / confirmed チェック
  //   3. #lockguard-execute-button -> executeLockGuardAction()
  //   4. fail-safeチェック: state!='ready' / blockId欠如 / confirmed未チェック -> message表示でstop
  //   5. 実行: exportBlock(blockId, authInfo) または deleteBlock(blockId, authInfo)
  //   6. 入力不足/認証不一致 (success=false): message表示, LockGuardは開いたまま維持, 再描画しない
  //   7. 実行例外 (throw): message表示, LockGuardは開いたまま維持, 再描画しない
  //   8. success=true: showServiceResultMessage -> resetLockGuard -> refreshAllViews(blockId)
  //   refreshAllViews 内訳:
  //     - renderBlockListEntry()   -> 一覧 / Export-Delete テーブル / 接続管理パネル
  //     - renderBlockDetailEntry() -> 選択中 block 詳細パネル
  //     - refreshDashboardViews()  -> Dashboard 集計 + 最近ログ
  //     - renderAuditLogRows()     -> Audit Log (export / delete 記録追加)
  //     - renderSecuritySettings() -> Settings 再描画
  const executeLockGuardAction = async () => {
    const { state: lockGuardState, actionType, blockId } = getLockGuardState();
    const authInfo = getLockGuardAuthInfo();

    // fail-safe: invalid panel state -> stop without service call
    if (lockGuardState !== 'ready') {
      showOperationMessage(uiText.msgLockGuardInvalidState, false);
      return;
    }

    // fail-safe: target/action missing -> stop without service call
    if (!blockId || (actionType !== 'export' && actionType !== 'delete')) {
      showOperationMessage(uiText.msgLockGuardMissingTarget, false);
      return;
    }

    // fail-safe: final confirmation missing -> stop without service call
    if (!lockGuardConfirmed?.checked || !authInfo.confirmed) {
      showOperationMessage(uiText.msgConfirmRequired, false);
      return;
    }

    const actionHandler = actionType === 'delete'
      ? serviceCommands.deleteBlock
      : serviceCommands.exportBlock;
    const pendingKey = `${blockId}:${actionType}`;

    if (pendingBlockActions.has(pendingKey)) return;

    pendingBlockActions.add(pendingKey);
    if (lockGuardExecuteButton) lockGuardExecuteButton.disabled = true;
    let executionSucceeded = false;

    try {
      const result = await actionHandler(blockId, authInfo);

      if (result?.success === false) {
        // fail-safe: 認証不足/不一致や API 側拒否を含む失敗時は message のみ表示して終了
        // - LockGuard は開いたまま維持して再入力可能
        // - executionSucceeded は false のままなので再描画は行わない
        showOperationMessage(result?.message || uiText.msgLockGuardFailed, false);
        return;
      }

      executionSucceeded = true;
      showServiceResultMessage(result);
      resetLockGuard();
    } catch {
      // fail-safe: 例外時も message のみ表示し、LockGuard は閉じずに再入力可能な状態を維持
      showOperationMessage(uiText.msgLockGuardFailed, false);
    } finally {
      pendingBlockActions.delete(pendingKey);
      if (lockGuardExecuteButton) lockGuardExecuteButton.disabled = false;
      if (executionSucceeded) {
        // 成功時のみ全体再描画する。失敗時は既存表示維持で安全側に倒す
        await refreshAllViews(blockId);
      }
    }
  };

  const refreshDashboardViews = async () => {
    await renderDashboardStats();
    await renderDashboardRecentLogs();
  };

  // Step1: 一覧描画入口（getBlocks async 前提）
  const renderBlockListEntry = async () => {
    await renderBlockRows();
    await renderExportDeleteRows();
    await renderConnectionManagementPanel();
  };

  // Step2: 詳細描画入口（getBlockById/getBlockDetailViewModel async 前提）
  const renderBlockDetailEntry = async (blockId = selectedBlockId) => {
    await renderSelectedBlockDetail(blockId);
  };

  const refreshBlockOperationViews = async (blockId = selectedBlockId) => {
    await renderBlockListEntry();
    await renderBlockDetailEntry(blockId);
  };

  const refreshAllViews = async (blockId = selectedBlockId) => {
    await Promise.allSettled([
      refreshBlockOperationViews(blockId),
      refreshDashboardViews(),
      renderAuditLogRows(),
      renderSecuritySettings()
    ]);
    showOperationMessage(lastOperationMessage, lastOperationMessageSuccess);
  };

  // Step3 接続/切断確認用: 成功/失敗にかかわらず再描画される範囲をここで追えるようにする
  // 通し確認フロー:
  //   1. renderBlockListEntry()   -> 一覧テーブル / Export-Delete テーブル / 接続管理パネル
  //   2. renderBlockDetailEntry() -> 選択中 block の詳細パネル
  //   3. refreshDashboardViews()  -> Dashboard 集計 + 最近ログ
  //   4. renderAuditLogRows()     -> Audit Log テーブル
  //   5. showOperationMessage()   -> 操作結果 message
  // 再描画対象:
  // - Block 一覧
  // - Block 詳細
  // - Dashboard
  // - 接続/切断管理
  // - Audit Log
  // - message
  // 異常系メモ:
  // - connect/disconnect 失敗時でも refreshConnectionActionViews() は呼ばれる
  // - 描画側は serviceQueries の fail-safe で失敗時更新を中断し、既存表示を維持する
  // - そのため UI は message 更新を優先しつつ、表示崩れを避ける
  const refreshConnectionActionViews = async (blockId = selectedBlockId) => {
    await Promise.allSettled([
      refreshBlockOperationViews(blockId),
      refreshDashboardViews(),
      renderAuditLogRows()
    ]);
    showOperationMessage(lastOperationMessage, lastOperationMessageSuccess);
  };

  // Step5 通し確認フロー (freeze / unfreeze 実行後):
  //   1. renderBlockListEntry()   -> 一覧テーブル (freezeStatus chip 更新)
  //   2. renderBlockDetailEntry() -> 選択中 block の詳細パネル (freezeStatus 更新)
  //   3. refreshDashboardViews()  -> Dashboard 集計 (frozenBlocks / activeBlocks カウント)
  //   4. renderAuditLogRows()     -> Audit Log (freeze / unfreeze 記録追加)
  //   5. renderSecuritySettings() -> Settings 再描画 (副作用なし)
  //   6. showOperationMessage()   -> 操作結果 message
  const refreshFreezeActionViews = async (blockId = selectedBlockId) => {
    await refreshAllViews(blockId);
  };

  // Step5 freeze/unfreeze 実行フロー確認ガイド:
  // 1. renderFreezeWarning() -> 警告表示 + freezeWarningSection にblockId/actionType を保持
  // 2. freezeWarningConfirm.checked == true -> 実行ボタンが有効になる
  // 3. executeFreezeWarningAction() -> fail-safe チェック -> actionHandler(blockId) await
  // 4. result.success === true -> showServiceResultMessage -> resetFreezeWarning -> refreshFreezeActionViews
  // 4'. result.success !== true or throw -> showOperationMessage (fail-safe, 警告表示維持 + 再描画なし)
  const executeFreezeWarningAction = async () => {
    const { actionType, blockId } = getFreezeWarningState();

    // fail-safe: target/action missing -> stop without service call
    if (!blockId || (actionType !== 'freeze' && actionType !== 'unfreeze')) {
      showOperationMessage(uiText.msgFreezeMissingTarget, false);
      return;
    }

    // fail-safe: confirmation missing -> stop without service call
    if (!freezeWarningConfirm?.checked) {
      showOperationMessage(uiText.msgConfirmRequired, false);
      return;
    }

    const actionHandler = actionType === 'freeze'
      ? serviceCommands.freezeBlock
      : serviceCommands.unfreezeBlock;
    const pendingKey = `${blockId}:${actionType}`;
    if (pendingBlockActions.has(pendingKey)) return;

    pendingBlockActions.add(pendingKey);
    if (freezeWarningExecute) freezeWarningExecute.disabled = true;
    let executionSucceeded = false;

    try {
      const result = await actionHandler(blockId);
      const isSuccess = result?.success === true;

      if (!isSuccess) {
        showOperationMessage(result?.message || uiText.msgFreezeFailed, false);
        return;
      }

      executionSucceeded = true;
      showServiceResultMessage(result);
      resetFreezeWarning();
    } catch {
      showOperationMessage(uiText.msgFreezeFailed, false);
    } finally {
      pendingBlockActions.delete(pendingKey);
      if (freezeWarningExecute) freezeWarningExecute.disabled = false;
      if (executionSucceeded) {
        await refreshFreezeActionViews(blockId);
      }
    }
  };

  // ---- Block detail rendering section ----
  // service calls: services.block.getBlockDetailViewModel

  const formatDetailValue = (key, value) => {
    if (value == null || value === '') return '-';
    if (key === 'updatedAt' && typeof value === 'string') {
      return value.replace('T', ' ').slice(0, 16);
    }
    if (typeof value === 'boolean') {
      return value ? 'true' : 'false';
    }
    return String(value);
  };

  const renderDetailFields = (prefix, detail) => {
    detailFieldKeys.forEach((key) => {
      const field = document.getElementById(`${prefix}-${key}`);
      if (!field) return;
      field.textContent = formatDetailValue(key, detail?.[key]);
    });
  };

  const renderDashboardBlockDetail = (detail) => {
    const placeholder = domRefs.dashboardBlockDetailPlaceholder;
    const handshakeField = domRefs.dashboardDetailHandshakeStatus;
    if (placeholder) {
      placeholder.textContent = detail ? uiText.blockDetailSelected : uiText.blockDetailEmpty;
    }
    if (handshakeField) {
      handshakeField.textContent = detail?.handshakeStatus ?? uiText.handshakeStatusDefault;
    }
    renderDetailFields('dashboard-detail', detail);
  };

  const renderBlockManagementDetail = (detail) => {
    const panel = domRefs.blockDetailPanel;
    const placeholder = domRefs.blockDetailPlaceholder;
    const handshakeField = domRefs.blockDetailHandshakeStatus;
    if (!panel) return;

    panel.hidden = !detail;
    if (placeholder) {
      placeholder.textContent = detail ? uiText.blockDetailSelected : uiText.blockDetailEmpty;
    }
    if (handshakeField) {
      handshakeField.textContent = detail?.handshakeStatus ?? uiText.handshakeStatusDefault;
    }
    renderDetailFields('detail', detail);
  };

  const clearBlockDetailPanels = () => {
    renderDashboardBlockDetail(null);
    renderBlockManagementDetail(null);
  };

  const renderSelectedBlockDetail = async (blockId) => {
    const requestedBlockId = setSelectedBlockId(blockId);
    const requestSeq = ++blockDetailRequestSeq;

    if (!requestedBlockId) {
      // 明示的に未選択へ戻す操作では、詳細パネルをプレースホルダーへ復帰する
      clearBlockDetailPanels();
      return;
    }

    try {
      const detailResult = await serviceQueries.getBlockDetailViewModel(requestedBlockId);
      if (requestSeq !== blockDetailRequestSeq || selectedBlockId !== requestedBlockId) {
        return;
      }

      if (!detailResult.ok) {
        // Step2 異常系: 詳細取得失敗 -> message 表示 + 詳細パネルをプレースホルダー復帰
        showOperationMessage(uiText.msgBlockDetailLoadFailed, false);
        clearBlockDetailPanels();
        return;
      }

      const detail = detailResult.data;
      if (!detail || typeof detail !== 'object') {
        showOperationMessage(uiText.msgBlockDetailLoadFailed, false);
        clearBlockDetailPanels();
        return;
      }

      renderDashboardBlockDetail(detail);
      renderBlockManagementDetail(detail);
    } catch {
      if (requestSeq !== blockDetailRequestSeq || selectedBlockId !== requestedBlockId) {
        return;
      }
      // Step2 異常系: 詳細取得例外 -> message 表示 + 詳細パネルをプレースホルダー復帰
      showOperationMessage(uiText.msgBlockDetailLoadFailed, false);
      clearBlockDetailPanels();
    }
  };

  const refreshSelectedBlockDetail = async (blockId = selectedBlockId) => {
    const targetBlockId = normalizeSelectedBlockId(blockId);
    if (!selectedBlockId || !targetBlockId || selectedBlockId !== targetBlockId) return;
    await renderSelectedBlockDetail(selectedBlockId);
  };

  // ---- Settings section ----
  // service calls: services.log.getSecuritySettings

  const renderSecuritySettings = async () => {
    const placeholder = domRefs.settingsPanelPlaceholder;
    if (placeholder) {
      placeholder.textContent = uiText.settingsLoading;
    }

      const settingsResult = await loadSecuritySettingsForView();

      if (!settingsResult.ok) {
        if (placeholder) placeholder.textContent = uiText.settingsUnavailable;
        return;
      }

      const settings = settingsResult.data;

    if (!settings || typeof settings !== 'object') {
      if (placeholder) placeholder.textContent = uiText.settingsUnavailable;
      return;
    }

    if (placeholder) {
      placeholder.textContent = uiText.settingsReady;
    }

    const checkboxFields = [
      'passwordProtectionEnabled',
      'twoFactorEnabled',
      'handshakeRequired',
      'dangerousActionLock'
    ];

    checkboxFields.forEach((key) => {
      const element = document.getElementById(`settings-${key}`);
      if (!element) return;
      element.checked = Boolean(settings?.[key]);
    });

    const retentionField = document.getElementById('settings-auditLogRetentionDays');
    if (retentionField) {
      retentionField.value = settings?.auditLogRetentionDays ?? '';
    }
  };

  // ---- Audit log section ----
  // service calls: services.log.getAuditLogs / getAuditLogViewItems / getAuditLogCount

  const getAuditLogFilter = () => ({
    action: (auditLogFilterAction?.value ?? '').trim(),
    result: (auditLogFilterResult?.value ?? '').trim()
  });

  const getAuditLogResultClass = (result) => {
    const normalizedResult = String(result ?? '').trim().toLowerCase();

    if (normalizedResult === 'ok' || normalizedResult === 'success') {
      return 'is-success';
    }

    if (normalizedResult === 'failed' || normalizedResult === 'failure' || normalizedResult === 'error') {
      return 'is-failure';
    }

    return '';
  };

  // Step4 実動確認: 取得系 async 呼び出しを追いやすくする
  const loadAuditLogViewItemsAndCount = async (filter) => {
    const [auditLogItemsResult, auditLogCountResult] = await Promise.all([
      serviceQueries.getAuditLogViewItems(filter),
      serviceQueries.getAuditLogCount(filter)
    ]);

    return { auditLogItemsResult, auditLogCountResult };
  };

  const loadSecuritySettingsForView = async () => serviceQueries.getSecuritySettings();
  const saveSecuritySettingsForView = async (nextSettings) => serviceQueries.updateSecuritySettings(nextSettings);

  const renderAuditLogRows = async () => {
      const auditLogsResult = await serviceQueries.getAuditLogs();
      if (!auditLogsResult.ok || !Array.isArray(auditLogsResult.data)) {
        const dashboardBody = domRefs.dashboardAuditLogBody;
        if (dashboardBody && !String(dashboardBody.innerHTML ?? '').trim()) {
          dashboardBody.innerHTML = `<tr><td colspan="4">${uiText.dashboardAuditEmpty}</td></tr>`;
        }

        const auditListBody = domRefs.auditLogListBody;
        if (auditListBody && !String(auditListBody.innerHTML ?? '').trim()) {
          auditListBody.innerHTML = `<tr><td colspan="5">${uiText.filteredAuditEmpty}</td></tr>`;
        }
        return;
      }

      const auditLogs = auditLogsResult.data;
    const latestLogs = auditLogs.slice(-5).reverse();
    const logHtml = latestLogs.map((log) => `
      <tr>
        <td>${(log.timestamp ?? '').replace('T', ' ').slice(0, 16)}</td>
        <td>${log.action ?? '-'}</td>
        <td>${log.target ?? '-'}</td>
        <td>${log.result ?? '-'}</td>
      </tr>
    `).join('');

    const auditBody = domRefs.dashboardAuditLogBody;
    if (auditBody) {
      auditBody.innerHTML = logHtml || `<tr><td colspan="4">${uiText.dashboardAuditEmpty}</td></tr>`;
    }

    const filter = getAuditLogFilter();
    const { auditLogItemsResult, auditLogCountResult } = await loadAuditLogViewItemsAndCount(filter);

      if (!auditLogItemsResult.ok || !auditLogCountResult.ok) return;

      const auditLogItems = Array.isArray(auditLogItemsResult.data) ? auditLogItemsResult.data : [];
      const auditLogItemCount = Number.isFinite(Number(auditLogCountResult.data)) ? Number(auditLogCountResult.data) : 0;

    if (auditLogCount) {
      auditLogCount.textContent = String(auditLogItemCount);
    }

    const auditListBody = domRefs.auditLogListBody;
    if (auditListBody) {
      const listHtml = auditLogItems.map((log) => {
        const resultClass = getAuditLogResultClass(log.result);
        const resultState = String(log.result ?? '').trim().toLowerCase();

        return `
        <tr>
          <td>${(log.timestamp ?? '').replace('T', ' ').slice(0, 16)}</td>
          <td>${log.operator ?? '-'}</td>
          <td>${log.target ?? '-'}</td>
          <td>${log.action ?? '-'}</td>
          <td class="${resultClass}" data-result="${resultState}">${log.result ?? '-'}</td>
        </tr>
      `;
      }).join('');

      auditListBody.innerHTML = listHtml || `<tr><td colspan="5">${uiText.filteredAuditEmpty}</td></tr>`;
    }
  };

  const collectSecuritySettingsFormValue = () => {
    const getChecked = (id) => Boolean(document.getElementById(id)?.checked);
    const retentionField = document.getElementById('settings-auditLogRetentionDays');

    return {
      passwordProtectionEnabled: getChecked('settings-passwordProtectionEnabled'),
      twoFactorEnabled: getChecked('settings-twoFactorEnabled'),
      auditLogRetentionDays: Number.isFinite(Number(retentionField?.value))
        ? Number(retentionField.value)
        : 0,
      handshakeRequired: getChecked('settings-handshakeRequired'),
      dangerousActionLock: getChecked('settings-dangerousActionLock')
    };
  };

  // Step4 通し確認フロー (Settings 保存後):
  //   1. PUT /settings/security -> saveSecuritySettingsForView()
  //   2. 成功: renderSecuritySettings() -> フォームに最新値を再反映
  //   3. 成功: renderAuditLogRows()     -> Audit Log に settings 操作記録を反映
  //   4. 成功: showOperationMessage()   -> 保存成功 message
  //   失敗: showOperationMessage (fail-safe) -> renderSecuritySettings / renderAuditLogRows は呼ばない
  const saveSecuritySettings = async () => {
    const saveButton = domRefs.settingsSaveButton;
    if (saveButton) saveButton.disabled = true;

    try {
      const nextSettings = collectSecuritySettingsFormValue();
      const saveResult = await saveSecuritySettingsForView(nextSettings);

      if (!saveResult.ok) {
        showOperationMessage(uiText.msgSettingsSaveFailed, false);
        return;
      }

      await renderSecuritySettings();
      await renderAuditLogRows();
      showOperationMessage(uiText.msgSettingsSaved, true);
    } catch {
      showOperationMessage(uiText.msgSettingsSaveFailed, false);
    } finally {
      if (saveButton) saveButton.disabled = false;
    }
  };

  // ---- Navigation / event binding section (no service calls) ----

  const bindNavigation = () => {
    const navLinks = document.querySelectorAll('[data-nav]');
    const pageContainers = [
      domRefs.dashboardPage,
      domRefs.blocksPage,
      domRefs.connectionsPage,
      domRefs.exportDeletePage,
      domRefs.auditPage,
      domRefs.settingsPage
    ].filter(Boolean);
    const topbarTitle = domRefs.topbarTitle;

    const navTitles = {
      dashboard:       'ダッシュボード',
      blocks:          'Block管理',
      connections:     '接続/切断管理',
      'export-delete': 'Export/Delete管理',
      audit:           'Audit Log',
      settings:        'Security/Settings'
    };

    const activatePage = (target) => {
      pageContainers.forEach((page) => {
        page.hidden = page.dataset.page !== target;
      });
      navLinks.forEach((link) => {
        link.classList.toggle('is-active', link.dataset.nav === target);
      });
      if (topbarTitle) topbarTitle.textContent = navTitles[target] ?? target;
    };

    navLinks.forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        activatePage(link.dataset.nav);
      });
    });

    // 初期状態を確定
    activatePage('dashboard');
  };

  const bindAuditLogFilters = () => {
    const handleAuditLogFilterChange = async () => {
      await renderAuditLogRows();
    };

    [auditLogFilterAction, auditLogFilterResult].forEach((field) => {
      if (!field) return;
      field.addEventListener('input', handleAuditLogFilterChange);
      field.addEventListener('change', handleAuditLogFilterChange);
    });
  };

  const bindSettingsActions = () => {
    const saveButton = domRefs.settingsSaveButton;
    if (!saveButton) return;

    saveButton.addEventListener('click', async () => {
      await saveSecuritySettings();
    });
  };

  // ---- Dashboard / block list rendering section ----
  // service calls: services.block.getBlockDashboardStats / getBlocks / getConnectionManagementItems
  //               services.log.getAuditLogs / getRecentAuditLogs

  const renderDashboardStats = async () => {
    const statsResult = await serviceQueries.getBlockDashboardStats();
    if (!statsResult.ok || !statsResult.data || typeof statsResult.data !== 'object') return;

    const stats = statsResult.data;
    setDashboardValue('totalBlocks', String(stats?.totalBlocks ?? 0));
    setDashboardValue('connectedBlocks', String(stats?.connectedBlocks ?? 0));
    setDashboardValue('disconnectedBlocks', String(stats?.disconnectedBlocks ?? 0));
    setDashboardValue('frozenBlocks', String(stats?.frozenBlocks ?? 0));
    setDashboardValue('activeBlocks', String(stats?.activeBlocks ?? 0));
    setDashboardValue('deleteRequestedBlocks', String(stats?.deleteRequestedBlocks ?? 0));
  };

  const renderDashboardRecentLogs = async () => {
    const recentLogElement = domRefs.dashboardRecentLog;
    if (!recentLogElement) return;

    const recentLogsResult = await serviceQueries.getRecentAuditLogs(5);

    if (!recentLogsResult.ok) return;

    const recentLogs = Array.isArray(recentLogsResult.data)
      ? recentLogsResult.data
      : [];

    if (!Array.isArray(recentLogs) || recentLogs.length === 0) {
      recentLogElement.textContent = uiText.dashboardRecentLogEmpty;
      return;
    }

    recentLogElement.style.whiteSpace = 'pre-line';
    recentLogElement.textContent = recentLogs
      .slice(0, 5)
      .map((log) => {
        const timestamp = (log.timestamp ?? '').replace('T', ' ').slice(0, 16) || '-';
        return `${timestamp} | ${log.action ?? '-'} | ${log.target ?? '-'} | ${log.result ?? '-'}`;
      })
      .join('\n');
  };

  const renderBlockRows = async () => {
      const blocksResult = await serviceQueries.getBlocks();
      // Step1 異常系: 一覧取得失敗時は message 表示のみ（serviceQueries側）で既存表示を維持する
      if (!blocksResult.ok || !Array.isArray(blocksResult.data)) return;

      const blocks = normalizeBlockListForView(blocksResult.data);
    const rowHtml = blocks.map((block) => `
      <tr>
        <td>${block.name}</td>
        <td>${block.type}</td>
        <td><span class="status-chip ${statusChipClass[block.status] ?? 'is-warn'}">${statusLabel[block.status] ?? block.status}</span></td>
        <td><span class="connect-chip ${connectionChipClass[block.connectionStatus] ?? 'is-disconnected'}">${connectionLabel[block.connectionStatus] ?? block.connectionStatus}</span></td>
        <td><span class="status-chip ${freezeChipClass[block.freezeStatus] ?? 'is-warn'}">${freezeLabel[block.freezeStatus] ?? block.freezeStatus}</span></td>
        <td>${formatTableDateTime(block.updatedAt)}</td>
        <td>
          <div class="table-actions">
            <button class="table-action is-secondary" type="button" data-detail-trigger="block" data-block-id="${block.id}">詳細</button>
            <button class="table-action is-connect" type="button" data-action="connect" data-block-id="${block.id}" ${pendingBlockActions.has(`${block.id}:connect`) ? 'disabled' : ''}>Connect</button>
            <button class="table-action is-disconnect" type="button" data-action="disconnect" data-block-id="${block.id}" ${pendingBlockActions.has(`${block.id}:disconnect`) ? 'disabled' : ''}>Disconnect</button>
            <button class="table-action is-connect" type="button" data-action="freeze" data-block-id="${block.id}" ${pendingBlockActions.has(`${block.id}:freeze`) ? 'disabled' : ''}>Freeze</button>
            <button class="table-action is-disconnect" type="button" data-action="unfreeze" data-block-id="${block.id}" ${pendingBlockActions.has(`${block.id}:unfreeze`) ? 'disabled' : ''}>Unfreeze</button>
          </div>
        </td>
      </tr>
    `).join('');

    const dashboardBody = domRefs.dashboardBlocksBody;
    const blocksBody = domRefs.blocksTableBody ?? document.querySelector('#blocks-table tbody');

    if (dashboardBody) dashboardBody.innerHTML = rowHtml;
    if (blocksBody) blocksBody.innerHTML = rowHtml;
  };

  const renderExportDeleteRows = async () => {
    const tableBody = domRefs.exportDeleteTableBody ?? document.querySelector('#exportdel-table tbody');
    if (!tableBody) return;

      const blocksResult = await serviceQueries.getBlocks();
      // Step1 異常系: 一覧取得失敗時は message 表示のみ（serviceQueries側）で既存表示を維持する
      if (!blocksResult.ok || !Array.isArray(blocksResult.data)) return;

      const blocks = normalizeBlockListForView(blocksResult.data);
    if (!Array.isArray(blocks) || blocks.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="4">${uiText.tableEmpty}</td></tr>`;
      return;
    }

    tableBody.innerHTML = blocks.map((block) => `
      <tr>
        <td>${block.name ?? '-'}</td>
        <td>${block.type ?? '-'}</td>
        <td><span class="status-chip ${statusChipClass[block.status] ?? 'is-warn'}">${statusLabel[block.status] ?? block.status ?? '-'}</span></td>
        <td>
          <div class="table-actions">
            <button class="table-action is-connect" type="button" data-lockguard-open="export" data-block-id="${block.id}" ${pendingBlockActions.has(`${block.id}:export`) ? 'disabled' : ''}>Export</button>
            <button class="table-action is-disconnect" type="button" data-lockguard-open="delete" data-block-id="${block.id}" ${pendingBlockActions.has(`${block.id}:delete`) ? 'disabled' : ''}>Delete</button>
          </div>
        </td>
      </tr>
    `).join('');
  };

  const renderConnectionManagementPanel = async () => {
    const list = domRefs.connectionManagementList;
    if (!list) return;

      const itemsResult = await serviceQueries.getConnectionManagementItems();
      if (!itemsResult.ok || !Array.isArray(itemsResult.data)) return;

      const items = itemsResult.data;
    if (!Array.isArray(items) || items.length === 0) {
      list.innerHTML = `<tr><td colspan="4">${uiText.connectionManagementEmpty}</td></tr>`;
      return;
    }

    list.innerHTML = items.map((item) => `
      <tr>
        <td>${item.name ?? '-'}</td>
        <td><span class="connect-chip ${connectionChipClass[item.connectionStatus] ?? 'is-disconnected'}">${connectionLabel[item.connectionStatus] ?? item.connectionStatus ?? '-'}</span></td>
        <td><span class="status-chip ${handshakeChipClass[item.handshakeStatus] ?? 'is-warn'}">${item.handshakeStatus ?? 'idle'}</span></td>
        <td>
          <div class="table-actions">
            <button class="table-action is-connect" type="button" data-action="connect-management" data-block-id="${item.id}">Connect</button>
            <button class="table-action is-disconnect" type="button" data-action="disconnect-management" data-block-id="${item.id}">Disconnect</button>
          </div>
        </td>
      </tr>
    `).join('');
  };

  // --- legacy danger stage overlays keyed by badge type (separate from LockGuard) ---
  const legacyDangerStages = {};
  document.querySelectorAll('.danger-modal-stage').forEach((el) => {
    const type = el.querySelector('.modal-badge')?.textContent.trim().toLowerCase();
    if (type) legacyDangerStages[type] = el;
  });
  if (!legacyDangerStages.export || !legacyDangerStages.delete) return;

  // --- apply legacy overlay positioning once at startup ---
  const overlayBase = {
    position: 'fixed', inset: '0', margin: '0',
    padding: '24px', placeItems: 'center', overflow: 'auto', zIndex: '1000',
  };
  legacyDangerStages.export.style.background = 'rgba(7,11,20,0.68)';
  legacyDangerStages.delete.style.background = 'rgba(37,10,14,0.74)';
  Object.values(legacyDangerStages).forEach((el) => {
    Object.assign(el.style, overlayBase);
    el.querySelector('.danger-modal-backdrop').style.width = 'min(680px,100%)';
  });

  // --- legacy overlay open / close (display:grid vs display:none, no hidden attribute conflict) ---
  const openLegacyDangerStage = (type) => { legacyDangerStages[type].style.display = 'grid'; };
  const closeLegacyDangerStages = () => Object.values(legacyDangerStages).forEach((el) => { el.style.display = 'none'; });

  const getLegacyDangerStageAuthInfo = (type) => {
    const modalRoot = legacyDangerStages[type]?.querySelector('[data-auth-modal]') ?? null;
    if (!modalRoot) {
      return {
        password: '',
        twoFactorCode: '',
        confirmationText: '',
        confirmed: false
      };
    }

    return {
      password: modalRoot.querySelector('[data-auth-field="password"]')?.value ?? '',
      twoFactorCode: modalRoot.querySelector('[data-auth-field="twoFactorCode"]')?.value ?? '',
      confirmationText: modalRoot.querySelector('[data-auth-field="confirmationText"]')?.value ?? '',
      confirmed: Boolean(modalRoot.querySelector('[data-auth-field="confirmed"]')?.checked)
    };
  };

  // initial state: all closed
  closeLegacyDangerStages();
  resetLockGuard();
  bindNavigation();
  bindAuditLogFilters();
  bindSettingsActions();

  // cancel buttons
  document.querySelectorAll('.modal-action.is-cancel').forEach((btn) => {
    btn.addEventListener('click', closeLegacyDangerStages);
  });

  // launcher buttons injected next to the section heading
  const heading = document.querySelector('.danger-modal-section .section-heading');
  if (heading) {
    heading.insertAdjacentHTML('beforeend',
      '<div class="table-actions">' +
        '<button type="button" class="table-action is-connect"    data-modal-open="export">Export</button>' +
        '<button type="button" class="table-action is-disconnect" data-modal-open="delete">Delete</button>' +
      '</div>'
    );
  }

  // legacy overlay open handler (background click is NOT wired → modal stays open)
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-modal-open]');
    if (btn && legacyDangerStages[btn.dataset.modalOpen]) {
      openLegacyDangerStage(btn.dataset.modalOpen);
      getLegacyDangerStageAuthInfo(btn.dataset.modalOpen);
    }
  });

  document.addEventListener('click', async (e) => {
    const lockGuardOpenButton = e.target.closest('[data-lockguard-open][data-block-id]');
    if (lockGuardOpenButton) {
      const hasMeta = renderLockGuard(lockGuardOpenButton.dataset.blockId, lockGuardOpenButton.dataset.lockguardOpen);
      showOperationMessage(
        hasMeta ? uiText.msgLockGuardOpened : uiText.msgLockGuardOpenFailed,
        hasMeta
      );
      return;
    }

    if (e.target.closest('#lockguard-execute-button')) {
      await executeLockGuardAction();
      return;
    }

    if (e.target.closest('#lockguard-cancel-button')) {
      resetLockGuard();
      return;
    }

    const warningActionButton = e.target.closest('[data-freeze-warning-action]');
    if (warningActionButton) {
      if (warningActionButton.dataset.freezeWarningAction === 'execute') {
        await executeFreezeWarningAction();
      }
      if (warningActionButton.dataset.freezeWarningAction === 'cancel') {
        resetFreezeWarning();
      }
      return;
    }

    const detailButton = e.target.closest('[data-detail-trigger][data-block-id]');
    if (detailButton) {
      await renderSelectedBlockDetail(detailButton.dataset.blockId);
      return;
    }

    const detailCloseButton = e.target.closest('[data-action="detail-close"]');
    if (detailCloseButton) {
      await renderSelectedBlockDetail(null);
      return;
    }

    const btn = e.target.closest('[data-action][data-block-id]');
    if (!btn) return;

    const actionHandlers = {
      connect: serviceCommands.connectBlock,
      disconnect: serviceCommands.disconnectBlock,
      // Step3 通し確認: 接続/切断管理パネルのボタンも同じ service 関数へ振る
      'connect-management': serviceCommands.connectBlock,
      'disconnect-management': serviceCommands.disconnectBlock
    };

    if (btn.dataset.action === 'freeze' || btn.dataset.action === 'unfreeze') {
      const hasMeta = renderFreezeWarning(btn.dataset.blockId, btn.dataset.action);
      showOperationMessage(
        hasMeta ? uiText.msgFreezeWarningShown : uiText.msgFreezeWarningShowFailed,
        hasMeta
      );
      return;
    }

    const actionHandler = actionHandlers[btn.dataset.action];
    if (!actionHandler) return;

    const pendingKey = `${btn.dataset.blockId}:${btn.dataset.action}`;
    if (pendingBlockActions.has(pendingKey)) return;

    const isHandshakeAction = btn.dataset.action === 'connect' || btn.dataset.action === 'disconnect'
      || btn.dataset.action === 'connect-management' || btn.dataset.action === 'disconnect-management';

    pendingBlockActions.add(pendingKey);
    btn.disabled = true;

    if (isHandshakeAction) {
      await serviceCommands.setHandshakeStatus(btn.dataset.blockId, 'pending');
      await refreshSelectedBlockDetail(btn.dataset.blockId);
    }

    try {
      const result = await actionHandler(btn.dataset.blockId);
      if (isHandshakeAction) {
        await serviceCommands.setHandshakeStatus(btn.dataset.blockId, result?.success === false ? 'failed' : 'success');
      }
      // success=false を含めて service 側 message を優先表示し、状態更新判断は再描画側へ委ねる
      showServiceResultMessage(result);
    } catch {
      if (isHandshakeAction) {
        await serviceCommands.setHandshakeStatus(btn.dataset.blockId, 'failed');
      }
      // 例外時は fail-safe: message 表示のみで処理継続（finally で安全に再描画）
      showOperationMessage(uiText.msgBlockActionFailed, false);
    } finally {
      pendingBlockActions.delete(pendingKey);
      // connect/disconnect は成功/失敗どちらでも再描画を試行し、失敗時は既存表示維持へ倒す
      await refreshConnectionActionViews(btn.dataset.blockId);
    }
  });

  refreshAllViews().catch(() => {
    showOperationMessage(uiText.msgBlockListLoadFailed, false);
  });
})();
