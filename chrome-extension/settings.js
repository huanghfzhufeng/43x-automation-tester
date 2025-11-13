/**
 * Settings Page - 43X Agent Tester
 * 
 * 负责配置管理和持久化
 */

console.log('⚙️ Settings 页面已加载');

// ============================================================================
// 默认配置
// ============================================================================

const DEFAULT_SETTINGS = {
  agentServiceUrl: 'http://localhost:8001',
  maxRounds: 50,
  inputDelay: 1000,
  messageTimeout: 60,
  autoRetry: true,
  debugMode: false,
  autoScreenshot: true
};

// ============================================================================
// DOM 元素
// ============================================================================

const elements = {
  backButton: document.getElementById('backButton'),
  settingsForm: document.getElementById('settingsForm'),
  resetButton: document.getElementById('resetButton'),
  statusMessage: document.getElementById('statusMessage'),
  
  // 表单字段
  agentServiceUrl: document.getElementById('agentServiceUrl'),
  maxRounds: document.getElementById('maxRounds'),
  inputDelay: document.getElementById('inputDelay'),
  messageTimeout: document.getElementById('messageTimeout'),
  autoRetry: document.getElementById('autoRetry'),
  debugMode: document.getElementById('debugMode'),
  autoScreenshot: document.getElementById('autoScreenshot')
};

// ============================================================================
// 初始化
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('📋 初始化设置页面');
  
  // 加载当前配置
  await loadSettings();
  
  // 绑定事件
  bindEvents();
});

// ============================================================================
// 事件绑定
// ============================================================================

function bindEvents() {
  // 返回按钮
  elements.backButton.addEventListener('click', () => {
    window.close();
  });
  
  // 表单提交
  elements.settingsForm.addEventListener('submit', handleSaveSettings);
  
  // 恢复默认
  elements.resetButton.addEventListener('click', handleResetSettings);
}

// ============================================================================
// 配置加载
// ============================================================================

async function loadSettings() {
  try {
    const result = await chrome.storage.local.get('settings');
    const settings = result.settings || DEFAULT_SETTINGS;
    
    // 填充表单
    elements.agentServiceUrl.value = settings.agentServiceUrl;
    elements.maxRounds.value = settings.maxRounds;
    elements.inputDelay.value = settings.inputDelay;
    elements.messageTimeout.value = settings.messageTimeout;
    elements.autoRetry.checked = settings.autoRetry;
    elements.debugMode.checked = settings.debugMode;
    elements.autoScreenshot.checked = settings.autoScreenshot;
    
    console.log('✅ 配置加载成功:', settings);
    
  } catch (error) {
    console.error('❌ 配置加载失败:', error);
    showMessage('配置加载失败', 'error');
  }
}

// ============================================================================
// 配置保存
// ============================================================================

async function handleSaveSettings(event) {
  event.preventDefault();
  
  try {
    // 收集表单数据
    const settings = {
      agentServiceUrl: elements.agentServiceUrl.value.trim(),
      maxRounds: parseInt(elements.maxRounds.value),
      inputDelay: parseInt(elements.inputDelay.value),
      messageTimeout: parseInt(elements.messageTimeout.value),
      autoRetry: elements.autoRetry.checked,
      debugMode: elements.debugMode.checked,
      autoScreenshot: elements.autoScreenshot.checked
    };
    
    // 验证配置
    if (!validateSettings(settings)) {
      return;
    }
    
    // 保存到 storage
    await chrome.storage.local.set({ settings });
    
    console.log('✅ 配置保存成功:', settings);
    showMessage('设置已保存', 'success');
    
    // 通知 background 配置已更新
    chrome.runtime.sendMessage({
      action: 'SETTINGS_UPDATED',
      settings
    });
    
  } catch (error) {
    console.error('❌ 配置保存失败:', error);
    showMessage('保存失败: ' + error.message, 'error');
  }
}

// ============================================================================
// 恢复默认
// ============================================================================

async function handleResetSettings() {
  if (!confirm('确定要恢复默认设置吗？')) {
    return;
  }
  
  try {
    // 保存默认配置
    await chrome.storage.local.set({ settings: DEFAULT_SETTINGS });
    
    // 重新加载表单
    await loadSettings();
    
    console.log('✅ 已恢复默认设置');
    showMessage('已恢复默认设置', 'success');
    
    // 通知 background
    chrome.runtime.sendMessage({
      action: 'SETTINGS_UPDATED',
      settings: DEFAULT_SETTINGS
    });
    
  } catch (error) {
    console.error('❌ 恢复默认设置失败:', error);
    showMessage('恢复失败: ' + error.message, 'error');
  }
}

// ============================================================================
// 配置验证
// ============================================================================

function validateSettings(settings) {
  // 验证 URL
  try {
    new URL(settings.agentServiceUrl);
  } catch (error) {
    showMessage('Service URL 格式不正确', 'error');
    return false;
  }
  
  // 验证数值范围
  if (settings.maxRounds < 1 || settings.maxRounds > 100) {
    showMessage('最大轮次必须在 1-100 之间', 'error');
    return false;
  }
  
  if (settings.inputDelay < 0 || settings.inputDelay > 10000) {
    showMessage('输入延迟必须在 0-10000 毫秒之间', 'error');
    return false;
  }
  
  if (settings.messageTimeout < 10 || settings.messageTimeout > 300) {
    showMessage('消息超时必须在 10-300 秒之间', 'error');
    return false;
  }
  
  return true;
}

// ============================================================================
// UI 辅助函数
// ============================================================================

function showMessage(text, type) {
  elements.statusMessage.textContent = text;
  elements.statusMessage.className = `status-message ${type}`;
  elements.statusMessage.style.display = 'block';
  
  // 3 秒后自动隐藏
  setTimeout(() => {
    elements.statusMessage.style.display = 'none';
  }, 3000);
}

console.log('✅ Settings 页面初始化完成');
