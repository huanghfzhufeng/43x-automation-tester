/**
 * Background Service Worker - 43X Agent Tester
 * 
 * 负责：
 * - 与 Python Agent Service 通信
 * - 管理测试状态
 * - 路由消息
 */

console.log('🚀 43X Agent Tester Background Service Worker 已加载');

// ============================================================================
// AgentServiceClient 类 - 与 Python Agent Service 通信
// ============================================================================

class AgentServiceClient {
  constructor(baseURL = 'http://localhost:8001') {
    this.baseURL = baseURL;
    this.sessionId = null;
  }

  /**
   * 启动测试
   */
  async startTest(scenarioConfig, filesContent = null) {
    console.log('🚀 启动测试:', scenarioConfig.scenario_name);
    
    // 构建请求数据
    const requestData = {
      scenario_config: scenarioConfig,
      files_content: filesContent
    };
    
    // 详细日志
    console.log('📤 发送数据到 Python Service:');
    console.log('  - scenario_config:', scenarioConfig);
    console.log('  - files_content:', filesContent);
    console.log('  - 完整请求:', JSON.stringify(requestData, null, 2));

    try {
      const response = await this.fetchWithRetry(`${this.baseURL}/api/test/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
      });

      const data = await response.json();
      this.sessionId = data.session_id;

      console.log('✅ 测试启动成功:', data);
      return data;

    } catch (error) {
      console.error('❌ 启动测试失败:', error);
      throw error;
    }
  }

  /**
   * 获取回答
   */
  async getAnswer(question) {
    if (!this.sessionId) {
      throw new Error('Session not started');
    }

    console.log('💬 请求回答...');
    console.log('⚠️ 发送的问题完整内容:', `[${question}]`);  // 用方括号包裹，方便看是否为空
    console.log('⚠️ 问题长度:', question ? question.length : 0);
    console.log('⚠️ 问题是否为空:', !question || question.trim() === '');

    try {
      const response = await this.fetchWithRetry(`${this.baseURL}/api/test/answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: this.sessionId,
          question: question
        })
      });

      const data = await response.json();
      console.log('✅ 收到回答:', data.answer.substring(0, 100) + '...');
      return data;

    } catch (error) {
      console.error('❌ 获取回答失败:', error);
      throw error;
    }
  }

  /**
   * 停止测试
   */
  async stopTest() {
    if (!this.sessionId) {
      return;
    }

    console.log('🛑 停止测试');

    try {
      await this.fetchWithRetry(`${this.baseURL}/api/test/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: this.sessionId
        })
      });

      console.log('✅ 测试已停止');
      this.sessionId = null;

    } catch (error) {
      console.error('❌ 停止测试失败:', error);
      throw error;
    }
  }

  /**
   * 获取状态
   */
  async getStatus() {
    if (!this.sessionId) {
      throw new Error('Session not started');
    }

    try {
      const response = await fetch(`${this.baseURL}/api/test/status/${this.sessionId}`);
      const data = await response.json();
      return data;

    } catch (error) {
      console.error('❌ 获取状态失败:', error);
      throw error;
    }
  }

  /**
   * 带重试的 fetch
   */
  async fetchWithRetry(url, options, maxRetries = 3, retryDelay = 2000) {
    let lastError;

    for (let i = 0; i < maxRetries; i++) {
      try {
        const response = await fetch(url, {
          ...options,
          signal: AbortSignal.timeout(30000) // 30 秒超时
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response;

      } catch (error) {
        lastError = error;
        console.warn(`⚠️ 请求失败 (${i + 1}/${maxRetries}):`, error.message);

        if (i < maxRetries - 1) {
          // 指数退避
          const delay = retryDelay * Math.pow(2, i);
          console.log(`⏳ ${delay}ms 后重试...`);
          await this.sleep(delay);
        }
      }
    }

    throw lastError;
  }

  /**
   * 睡眠函数
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ============================================================================
// TestOrchestrator 类 - 测试编排
// ============================================================================

class TestOrchestrator {
  constructor() {
    this.client = new AgentServiceClient();
    this.isRunning = false;
    this.currentTabId = null;
    this.stats = {
      rounds: 0,
      startTime: null,
      endTime: null,
      errors: []
    };
  }

  /**
   * 启动测试
   */
  async start(scenarioConfig, filesContent, tabId) {
    if (this.isRunning) {
      throw new Error('测试已在运行');
    }

    console.log('🚀 启动测试编排');
    this.isRunning = true;
    this.currentTabId = tabId;
    this.scenarioName = scenarioConfig.scenario_name;
    this.companyName = scenarioConfig.company_name;
    this.stats = {
      rounds: 0,
      startTime: Date.now(),
      endTime: null,
      errors: []
    };

    try {
      // 启动 Python Agent Service
      const result = await this.client.startTest(scenarioConfig, filesContent);

      // 通知 Content Script 开始监听
      try {
        await chrome.tabs.sendMessage(tabId, {
          action: 'START_MONITORING'
        });
        console.log('✅ Content Script 已通知');
      } catch (error) {
        console.warn('⚠️ 无法通知 Content Script:', error.message);
        console.warn('   Content Script 可能未加载，将在页面刷新后重试');
        // 不抛出错误，因为 Content Script 可能稍后加载
      }

      console.log('✅ 测试编排启动成功');
      return result;

    } catch (error) {
      this.isRunning = false;
      
      console.error('❌ 启动测试编排失败:', error);
      console.error('   错误详情:', error);
      
      // 只在真正的错误时保存日志（不包括 Content Script 通信错误）
      if (!error.message.includes('Could not establish connection')) {
        await saveTestLog({
          status: 'error',
          scenarioName: scenarioConfig.scenario_name,
          companyName: scenarioConfig.company_name,
          rounds: 0,
          elapsed: 0,
          error: error.message
        });
      }
      
      throw error;
    }
  }

  /**
   * 处理问题
   */
  async handleQuestion(question) {
    if (!this.isRunning) {
      console.warn('⚠️ 测试未运行，忽略问题');
      return;
    }

    this.stats.rounds++;
    console.log(`📝 处理问题 (Round ${this.stats.rounds})`);

    try {
      // 获取 Agent 回答
      const result = await this.client.getAnswer(question);
      // 发送回答到 Content Script（带重试与连接保护）
      await this.sendAnswerWithRetry(result.answer, 3, 1500);

      // 更新统计信息
      this.updateStats(result);

      console.log(`✅ Round ${this.stats.rounds} 完成`);

    } catch (error) {
      console.error('❌ 处理问题失败:', error);
      this.stats.errors.push({
        round: this.stats.rounds,
        error: error.message,
        timestamp: Date.now()
      });

      // 通知 Popup
      this.notifyPopup('ERROR', {
        message: error.message,
        round: this.stats.rounds
      });
    }
  }

  /**
   * 发送回答到 Content Script，支持重试与连接保护
   */
  async sendAnswerWithRetry(answer, maxRetries = 3, delayMs = 1000) {
    let lastError;
    for (let i = 0; i < maxRetries; i++) {
      try {
        await chrome.tabs.sendMessage(this.currentTabId, {
          action: 'SEND_ANSWER',
          answer
        });
        return;
      } catch (error) {
        lastError = error;
        const msg = (error && error.message) ? error.message : String(error);
        console.warn(`⚠️ 发送回答失败 (${i + 1}/${maxRetries}): ${msg}`);
        // 如果连接未建立，尝试重新通知 Content Script 启动监听
        if (msg.includes('Could not establish connection') || msg.includes('Receiving end does not exist')) {
          try {
            await chrome.tabs.sendMessage(this.currentTabId, { action: 'START_MONITORING' });
          } catch (_) {
            // 忽略
          }
        }
        // 退避等待后重试
        await this.sleep(delayMs * Math.pow(2, i));
      }
    }
    throw lastError || new Error('发送回答失败');
  }

  /**
   * 睡眠
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 停止测试
   */
  async stop(saveLog = true) {
    if (!this.isRunning) {
      return;
    }

    console.log('🛑 停止测试编排');
    this.isRunning = false;
    this.stats.endTime = Date.now();

    try {
      // 停止 Content Script 监听
      if (this.currentTabId) {
        await chrome.tabs.sendMessage(this.currentTabId, {
          action: 'STOP_MONITORING'
        }).catch(() => {
          // Content script 可能已卸载，忽略错误
        });
      }

      // 停止 Python Agent Service
      await this.client.stopTest();

      console.log('✅ 测试编排已停止');

      // 保存日志
      if (saveLog) {
        await saveTestLog({
          status: 'stopped',
          scenarioName: this.scenarioName,
          companyName: this.companyName,
          rounds: this.stats.rounds,
          elapsed: this.getStats().elapsed
        });
      }

      // 通知 Popup
      this.notifyPopup('STOPPED', this.getStats());

    } catch (error) {
      console.error('❌ 停止测试编排失败:', error);
    }
  }

  /**
   * 更新统计信息
   */
  updateStats(result) {
    // 通知 Popup 更新进度
    this.notifyPopup('PROGRESS', {
      rounds: this.stats.rounds,
      elapsed: Date.now() - this.stats.startTime,
      ...result
    });
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return {
      ...this.stats,
      elapsed: this.stats.endTime 
        ? this.stats.endTime - this.stats.startTime 
        : Date.now() - this.stats.startTime
    };
  }

  /**
   * 通知 Popup
   */
  notifyPopup(type, data) {
    chrome.runtime.sendMessage({
      action: 'UPDATE_STATUS',
      type: type,
      data: data
    }).catch(() => {
      // Popup 可能未打开，忽略错误
    });
  }
}

// ============================================================================
// 全局实例和配置
// ============================================================================

const orchestrator = new TestOrchestrator();
let currentSettings = null;

// ============================================================================
// 配置管理
// ============================================================================

async function loadSettings() {
  try {
    const result = await chrome.storage.local.get('settings');
    currentSettings = result.settings || {
      agentServiceUrl: 'http://localhost:8001',
      maxRounds: 50,
      inputDelay: 1000,
      messageTimeout: 60,
      autoRetry: true,
      debugMode: false,
      autoScreenshot: true
    };
    
    // 更新 AgentServiceClient 的 baseURL
    orchestrator.client.baseURL = currentSettings.agentServiceUrl;
    
    console.log('✅ 配置已加载:', currentSettings);
    return currentSettings;
    
  } catch (error) {
    console.error('❌ 加载配置失败:', error);
    return null;
  }
}

// 初始化时加载配置
loadSettings();

// ============================================================================
// 日志管理
// ============================================================================

async function saveTestLog(logData) {
  try {
    const result = await chrome.storage.local.get('testLogs');
    const logs = result.testLogs || [];
    
    // 添加新日志
    logs.unshift({
      timestamp: Date.now(),
      ...logData
    });
    
    // 只保留最近 50 条
    const trimmedLogs = logs.slice(0, 50);
    
    await chrome.storage.local.set({ testLogs: trimmedLogs });
    
    console.log('✅ 测试日志已保存');
    
  } catch (error) {
    console.error('❌ 保存日志失败:', error);
  }
}

// ============================================================================
// 消息监听
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('📨 收到消息:', request.action);

  // 来自 Popup 的消息
  if (request.action === 'START_TEST') {
    orchestrator.start(
      request.scenarioConfig,
      request.filesContent,
      request.tabId
    )
      .then(result => sendResponse({ success: true, data: result }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'STOP_TEST') {
    orchestrator.stop()
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'GET_STATS') {
    sendResponse({ success: true, data: orchestrator.getStats() });
    return true;
  }

  // 来自 Content Script 的消息
  if (request.action === 'NEW_QUESTION') {
    orchestrator.handleQuestion(request.question)
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'EVALUATION_COMPLETE') {
    console.log('🎉 评估完成:', request.stage);
    orchestrator.stop()
      .then(() => {
        const stats = orchestrator.getStats();
        
        // 保存日志
        saveTestLog({
          status: 'completed',
          scenarioName: request.scenarioName,
          companyName: request.companyName,
          stage: request.stage,
          rounds: stats.rounds,
          elapsed: stats.elapsed
        });
        
        orchestrator.notifyPopup('COMPLETED', {
          stage: request.stage,
          stats: stats
        });
        sendResponse({ success: true });
      });
    return true;
  }

  // 设置更新
  if (request.action === 'SETTINGS_UPDATED') {
    loadSettings()
      .then(() => sendResponse({ success: true }))
      .catch(error => sendResponse({ success: false, error: error.message }));
    return true;
  }

  // 获取当前配置
  if (request.action === 'GET_SETTINGS') {
    sendResponse({ success: true, settings: currentSettings });
    return true;
  }
});

// ============================================================================
// 健康检查
// ============================================================================

// 定期检查 Python Agent Service 是否可用
async function checkServiceHealth() {
  try {
    const response = await fetch('http://localhost:8001/health');
    if (response.ok) {
      console.log('✅ Python Agent Service 健康');
    } else {
      console.warn('⚠️ Python Agent Service 响应异常');
    }
  } catch (error) {
    console.warn('⚠️ Python Agent Service 不可用');
  }
}

// 每 120 秒检查一次（降低频率，减少服务端日志与请求压力）
setInterval(checkServiceHealth, 120000);

// 启动时检查一次
checkServiceHealth();

// 点击插件图标时打开独立窗口
chrome.action.onClicked.addListener(async (tab) => {
  // 检查是否在 43X 页面
  const validUrls = [
    'localhost:3000',
    '43x.ai',
    'www-dev-74d2c2a9.zenia.art'
  ];
  
  const isValidPage = tab.url && validUrls.some(url => tab.url.includes(url));
  
  if (!isValidPage) {
    // 如果不在 43X 页面，显示提示
    console.warn('⚠️ 当前不在 43X 页面');
  }
  
  // 打开独立窗口
  chrome.windows.create({
    url: chrome.runtime.getURL('popup.html'),
    type: 'popup',
    width: 450,
    height: 700,
    left: 100,
    top: 100
  });
});

console.log('✅ Background Service Worker 初始化完成');
