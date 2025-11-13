/**
 * Content Script - 43X Agent Tester
 * 
 * 注入到 43X 页面，负责：
 * - 监听投资人消息
 * - 提取问题文本
 * - 自动输入创业者回答
 * - 触发发送按钮
 */

console.log('🚀 43X Agent Tester Content Script 已加载');

// ============================================================================
// MessageMonitor 类 - 监听和提取消息
// ============================================================================

class MessageMonitor {
  constructor() {
    this.observer = null;
    this.lastMessageCount = 0;
    this.isRunning = false;
    this.messageContainer = null;
    // 已处理消息摘要，用于去重
    this.processedDigests = new Set();
    // 最近一次由我们发送的回答摘要，用于排除自我消息
    this.lastAnswerDigest = null;
  }

  /**
   * 启动消息监听
   */
  start() {
    if (this.isRunning) {
      console.log('⚠️ MessageMonitor 已在运行');
      return;
    }

    console.log('👀 启动消息监听...');
    this.isRunning = true;

    // 查找消息容器
    this.findMessageContainer();

    if (!this.messageContainer) {
      console.error('❌ 未找到消息容器');
      return;
    }

    // 创建 MutationObserver
    this.observer = new MutationObserver((mutations) => {
      this.handleMutations(mutations);
    });

    // 开始监听
    this.observer.observe(this.messageContainer, {
      childList: true,
      subtree: true
    });

    console.log('✅ 消息监听已启动');
    
    // 🔥 重要：检查页面上是否已经有消息
    // MutationObserver 只监听新变化，不会检测已存在的内容
    this.checkExistingMessages();
  }
  
  /**
   * 检查页面上已存在的消息
   */
  checkExistingMessages() {
    console.log('🔍 检查页面上已存在的消息...');
    
    // 🔥 关键修复：使用统一的 getAllMessages 方法
    const messages = this.getAllMessages();
    
    if (messages.length > 0) {
      console.log(`✅ 找到 ${messages.length} 个已存在的消息元素`);
      this.lastMessageCount = messages.length;
      
      // 提取最后一条消息
      const lastMessage = messages[messages.length - 1];
      const question = this.extractQuestion(lastMessage);
      
      if (question) {
        console.log('📨 检测到已存在的问题:', question.substring(0, 50) + '...');
        // 去重
        const digest = this.simpleDigest(question);
        if (!this.processedDigests.has(digest)) {
          this.processedDigests.add(digest);
          // 发送到 Background
          chrome.runtime.sendMessage({
            action: 'NEW_QUESTION',
            question: question
          });
        } else {
          console.log('ℹ️ 已存在消息已处理过，跳过');
        }
      }
    } else {
      console.log('ℹ️ 页面上暂无消息，等待新消息...');
    }
  }

  /**
   * 停止消息监听
   */
  stop() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    this.isRunning = false;
    console.log('🛑 消息监听已停止');
  }

  /**
   * 查找消息容器（每次都重新查找，确保引用有效）
   */
  findMessageContainer() {
    // 基于实际的 43X 前端结构
    // MessageBubble 组件会渲染在某个容器中
    const selectors = [
      'main',  // 主要内容区域
      '[class*="conversation"]',
      '[class*="message"]',
      '[class*="chat"]',
      '#root > div > div'  // React 根节点下的容器
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element) {
        this.messageContainer = element;
        console.log(`✅ 找到消息容器: ${selector}`);
        return element;
      }
    }

    // 如果都找不到，使用 body
    this.messageContainer = document.body;
    console.log('⚠️ 使用 body 作为消息容器');
    return this.messageContainer;
  }

  /**
   * 确保消息容器引用有效
   */
  ensureMessageContainer() {
    // 检查当前容器是否还在 DOM 中
    if (!this.messageContainer || !document.contains(this.messageContainer)) {
      console.log('🔄 消息容器失效，重新查找...');
      this.findMessageContainer();
    }
    return this.messageContainer;
  }

  /**
   * 处理 DOM 变化
   */
  handleMutations(mutations) {
    // 检查是否有新消息
    const messages = this.getAllMessages();
    
    if (messages.length > this.lastMessageCount) {
      console.log(`📨 检测到新消息: ${messages.length} (之前: ${this.lastMessageCount})`);
      
      // 🔥 关键修复：检查所有新增的消息，而不只是最后一条
      // 因为发送回答后，页面会同时新增：创业者的回答 + 投资人的新问题
      const newMessages = messages.slice(this.lastMessageCount);
      console.log(`🔍 检查 ${newMessages.length} 条新消息...`);
      
      // 遍历所有新消息，找到投资人的消息
      for (const newMessage of newMessages) {
        if (this.isInvestorMessage(newMessage)) {
          console.log('✅ 找到投资人的新消息');
          this.handleNewInvestorMessage(newMessage);
          break; // 只处理第一条投资人消息
        } else {
          console.log('⏭️  跳过非投资人消息');
        }
      }
      
      this.lastMessageCount = messages.length;
    }
  }

  /**
   * 获取所有消息元素
   */
  getAllMessages() {
    // 确保消息容器引用有效
    this.ensureMessageContainer();
    
    if (!this.messageContainer) {
      console.warn('⚠️ 消息容器未初始化');
      return [];
    }

    // 尝试多种选择器
    const selectors = [
      '[class*="MessageBubble"]',
      '[class*="message-bubble"]',
      '[class*="message"]',
      '[role="article"]',
      // 根据实际 DOM 结构，消息通常是 flex 布局的容器
      'main > div > [class*="flex"][class*="gap"]',
      // 更宽松的选择器
      'main [class*="flex"]',
      // 直接子元素
      'main > div > div'
    ];

    console.log('🔍 开始查找消息元素...');
    
    for (const selector of selectors) {
      const messages = this.messageContainer.querySelectorAll(selector);
      console.log(`   尝试选择器 "${selector}": 找到 ${messages.length} 个元素`);
      
      if (messages.length > 0) {
        // 过滤掉明显不是消息的元素
        const validMessages = Array.from(messages).filter(msg => {
          // 必须有文本内容（降低最小长度要求）
          const text = msg.textContent.trim();
          if (!text) return false;
          
          // 不能是输入框容器
          if (msg.querySelector('textarea')) return false;
          
          return true;
        });
        
        if (validMessages.length > 0) {
          console.log(`✅ 使用选择器 "${selector}" 找到 ${validMessages.length} 条有效消息`);
          return validMessages;
        } else {
          console.log(`   选择器 "${selector}" 的元素都被过滤掉了`);
        }
      }
    }

    // 如果所有选择器都失败，尝试最宽松的方式
    console.warn('⚠️ 所有选择器都失败，尝试最宽松的方式...');
    const allDivs = this.messageContainer.querySelectorAll('div');
    console.log(`   找到 ${allDivs.length} 个 div 元素`);
    
    const fallbackMessages = Array.from(allDivs).filter(div => {
      const text = div.textContent.trim();
      // 有足够的文本内容
      if (!text || text.length < 20) return false;
      // 不包含输入框
      if (div.querySelector('textarea')) return false;
      // 不是太深的嵌套（避免选中整个页面）
      const depth = this.getElementDepth(div);
      if (depth > 10) return false;
      return true;
    });
    
    if (fallbackMessages.length > 0) {
      console.log(`✅ 使用 fallback 方式找到 ${fallbackMessages.length} 条消息`);
      return fallbackMessages;
    }

    console.error('❌ 完全未找到任何消息元素');
    return [];
  }

  /**
   * 获取元素的嵌套深度
   */
  getElementDepth(element) {
    let depth = 0;
    let current = element;
    while (current && current !== this.messageContainer && depth < 20) {
      depth++;
      current = current.parentElement;
    }
    return depth;
  }

  /**
   * 判断是否是投资人的消息
   */
  isInvestorMessage(messageElement) {
    // 检查是否包含 "from-me" 类名（用户自己的消息）
    const classList = messageElement.className;
    if (classList.includes('from-me') || classList.includes('isFromMe')) {
      console.log('   ❌ 是用户自己的消息 (from-me)');
      return false;
    }

    // 检查是否是 divider 类型（阶段分隔线）
    if (classList.includes('divider')) {
      console.log('   ❌ 是阶段分隔线 (divider)');
      return false;
    }

    // 检查消息内容，如果为空或只有按钮，可能不是有效消息
    const text = messageElement.textContent.trim();
    if (!text || text.length < 10) {
      console.log('   ❌ 消息内容太短或为空');
      return false;
    }

    // 排除我们自己刚刚发送的回答（基于摘要匹配）
    const digest = this.simpleDigest(text);
    if (this.lastAnswerDigest && digest === this.lastAnswerDigest) {
      console.log('   ❌ 这是我们刚刚发送的回答，跳过');
      return false;
    }

    // 检查是否包含 textarea（输入框），如果有则不是消息
    const hasTextarea = messageElement.querySelector('textarea');
    if (hasTextarea) {
      console.log('   ❌ 包含输入框，不是消息');
      return false;
    }

    console.log('   ✅ 确认是投资人消息');
    return true;
  }

  /**
   * 处理新的投资人消息
   */
  async handleNewInvestorMessage(messageElement) {
    console.log('💬 收到投资人消息');

    // 等待消息完全加载（thinking 状态结束）
    await this.waitForMessageComplete(messageElement);

    // 提取问题文本
    const question = this.extractQuestion(messageElement);

    if (question) {
      console.log(`📝 提取到问题: ${question.substring(0, 100)}...`);
      
      // 去重：避免重复发送同一消息
      const digest = this.simpleDigest(question);
      if (this.processedDigests.has(digest)) {
        console.log('ℹ️ 重复消息，忽略');
        return;
      }
      this.processedDigests.add(digest);

      // 发送给 Background Script
      chrome.runtime.sendMessage({
        action: 'NEW_QUESTION',
        question: question
      });
    } else {
      console.warn('⚠️ 未能提取到问题文本');
    }
  }

  /**
   * 等待消息完全加载
   */
  async waitForMessageComplete(messageElement) {
    const maxWait = 60000; // 最多等待 60 秒
    const checkInterval = 500; // 每 500ms 检查一次
    let waited = 0;

    while (waited < maxWait) {
      // 检查是否还在 thinking 状态
      const thinkingElement = messageElement.querySelector('[data-status="thinking"]');
      if (!thinkingElement) {
        console.log('✅ 消息加载完成');
        return;
      }

      await this.sleep(checkInterval);
      waited += checkInterval;
    }

    console.warn('⚠️ 等待消息完成超时');
  }

  /**
   * 简单摘要函数（字符串哈希）
   */
  simpleDigest(str) {
    try {
      let hash = 0;
      const s = (str || '').toLowerCase().trim();
      for (let i = 0; i < s.length; i++) {
        hash = ((hash << 5) - hash) + s.charCodeAt(i);
        hash |= 0; // 32-bit 整数
      }
      return String(hash);
    } catch (e) {
      return String(Date.now());
    }
  }

  /**
   * 提取问题文本
   * 基于实际的 43X 前端结构：
   * - TextContent 组件包含实际文本
   * - ThinkingStep 组件需要过滤
   * - message.content.text 是实际内容
   */
  extractQuestion(messageElement) {
    // 克隆元素以避免修改原始 DOM
    const clonedElement = messageElement.cloneNode(true);
    
    // 移除 ThinkingStep 组件（思考过程）
    const thinkingSteps = clonedElement.querySelectorAll('[class*="ThinkingStep"]');
    thinkingSteps.forEach(step => step.remove());
    
    // 移除头像和名称
    const avatars = clonedElement.querySelectorAll('[class*="Avatar"]');
    avatars.forEach(avatar => avatar.remove());
    
    // 移除按钮
    const buttons = clonedElement.querySelectorAll('button');
    buttons.forEach(button => button.remove());
    
    // 尝试查找 TextContent 组件
    const textContentSelectors = [
      '[class*="TextContent"]',
      '[class*="text-content"]',
      '.text-content'
    ];
    
    for (const selector of textContentSelectors) {
      const textElement = clonedElement.querySelector(selector);
      if (textElement) {
        const text = textElement.textContent.trim();
        if (text && text.length > 0) {
          console.log('📝 提取到文本 (TextContent):', text.substring(0, 50) + '...');
          return text;
        }
      }
    }
    
    // 如果没找到 TextContent，尝试获取所有文本
    const text = clonedElement.textContent.trim();
    if (text && text.length > 0) {
      console.log('📝 提取到文本 (fallback):', text.substring(0, 50) + '...');
      return text;
    }
    
    console.warn('⚠️ 未能提取到文本内容');
    return null;
  }

  /**
   * 睡眠函数
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ============================================================================
// AutoInput 类 - 自动输入和发送
// ============================================================================

class AutoInput {
  constructor() {
    this.textarea = null;
    this.sendButton = null;
  }

  /**
   * 查找输入框和发送按钮
   * 基于实际的 43X MessageInput 组件结构
   */
  findElements() {
    // 查找 textarea - 根据 placeholder 精确匹配
    const textareas = document.querySelectorAll('textarea');
    for (const textarea of textareas) {
      const placeholder = textarea.getAttribute('placeholder');
      if (placeholder && placeholder.includes('输入消息')) {
        this.textarea = textarea;
        console.log('✅ 找到输入框:', placeholder);
        break;
      }
    }
    
    // 如果没找到特定的，使用最后一个 textarea
    if (!this.textarea && textareas.length > 0) {
      this.textarea = textareas[textareas.length - 1];
      console.log('✅ 找到输入框 (fallback)');
    }
    
    if (!this.textarea) {
      console.error('❌ 未找到输入框');
      return false;
    }

    // 查找发送按钮 - 精确匹配文本
    const buttons = document.querySelectorAll('button');
    for (const button of buttons) {
      const buttonText = button.textContent.trim();
      if (buttonText === '发送' || buttonText === 'Send') {
        this.sendButton = button;
        console.log('✅ 找到发送按钮:', buttonText);
        break;
      }
    }

    if (!this.sendButton) {
      console.error('❌ 未找到发送按钮');
      return false;
    }

    return true;
  }

  /**
   * 填充输入框
   */
  async fillTextarea(text) {
    if (!this.findElements()) {
      throw new Error('未找到输入框或发送按钮');
    }

    console.log(`📝 填充输入框: ${text.substring(0, 50)}...`);

    // 方法 1: 使用 React 的方式设置值
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      'value'
    ).set;
    
    nativeInputValueSetter.call(this.textarea, text);

    // 触发 React 事件
    this.triggerReactEvent(this.textarea, 'input');
    this.triggerReactEvent(this.textarea, 'change');

    // 等待一下确保 React 状态更新
    await this.sleep(500);

    console.log('✅ 输入框填充完成');
  }

  /**
   * 触发 React 事件
   */
  triggerReactEvent(element, eventType) {
    const event = new Event(eventType, { bubbles: true });
    element.dispatchEvent(event);
  }

  /**
   * 点击发送按钮
   */
  async clickSendButton() {
    if (!this.sendButton) {
      throw new Error('未找到发送按钮');
    }

    // 检查按钮是否可用
    if (this.sendButton.disabled) {
      console.warn('⚠️ 发送按钮被禁用，等待...');
      await this.waitForButtonEnabled();
    }

    console.log('🖱️ 点击发送按钮');
    this.sendButton.click();

    // 等待消息发送
    await this.sleep(1000);

    console.log('✅ 消息已发送');
  }

  /**
   * 等待按钮可用
   */
  async waitForButtonEnabled() {
    const maxWait = 10000; // 最多等待 10 秒
    const checkInterval = 500;
    let waited = 0;

    while (waited < maxWait) {
      if (!this.sendButton.disabled) {
        return;
      }
      await this.sleep(checkInterval);
      waited += checkInterval;
    }

    throw new Error('等待发送按钮可用超时');
  }

  /**
   * 睡眠函数
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ============================================================================
// CompletionDetector 类 - 检测评估完成
// ============================================================================

class CompletionDetector {
  /**
   * 检测评估是否完成
   * 基于实际的 43X 前端结构：
   * - MessageType.divider 表示阶段分隔线
   * - STAGE_NAME_MAP 包含阶段名称
   * - 背景图片: stageDivider.png
   */
  isEvaluationComplete() {
    // 方法 1: 检测阶段分隔线（divider）
    // 查找包含阶段名称的元素
    const stageElements = document.querySelectorAll('[class*="h-7"][class*="w-38"]');
    if (stageElements.length > 0) {
      const lastStage = stageElements[stageElements.length - 1];
      const text = lastStage.textContent.trim();
      
      console.log('🔍 检测到阶段:', text);
      
      // 检查是否是最终阶段
      if (text.includes('决策') || text.includes('完成') || text.includes('结束')) {
        console.log('✅ 检测到评估完成（阶段分隔线）');
        return true;
      }
    }

    // 方法 2: 检测虚线分隔符
    const dividers = document.querySelectorAll('[class*="border-dashed"]');
    if (dividers.length >= 2) {
      // 查找相邻的两个虚线之间的文本
      for (let i = 0; i < dividers.length - 1; i++) {
        const current = dividers[i];
        const next = dividers[i + 1];
        
        // 获取两个虚线之间的元素
        let sibling = current.nextElementSibling;
        while (sibling && sibling !== next) {
          const text = sibling.textContent.trim();
          if (text && (text.includes('决策') || text.includes('完成'))) {
            console.log('✅ 检测到评估完成（虚线分隔符）:', text);
            return true;
          }
          sibling = sibling.nextElementSibling;
        }
      }
    }

    // 方法 3: 检测消息内容关键词
    const messages = document.querySelectorAll('[class*="flex"][class*="gap-4"]');
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const text = lastMessage.textContent;
      
      if (text.includes('评估完成') || text.includes('决策完成') || text.includes('投资决策')) {
        console.log('✅ 检测到评估完成（消息关键词）');
        return true;
      }
    }

    return false;
  }

  /**
   * 获取当前评估阶段
   * 基于 STAGE_NAME_MAP 的阶段名称
   */
  getCurrentStage() {
    // 查找阶段分隔线元素
    const stageElements = document.querySelectorAll('[class*="h-7"][class*="w-38"]');
    if (stageElements.length > 0) {
      const lastStage = stageElements[stageElements.length - 1];
      const text = lastStage.textContent.trim();
      
      console.log('📊 当前阶段:', text);
      return text;
    }
    
    // 备用方法：查找包含阶段名称的任何元素
    const allElements = document.querySelectorAll('*');
    for (const element of allElements) {
      const text = element.textContent.trim();
      if (text.length < 20) {  // 阶段名称通常很短
        if (text.includes('初评') || text.includes('初步评估')) return '初评';
        if (text.includes('深评') || text.includes('深度评估')) return '深评';
        if (text.includes('尽调') || text.includes('尽职调查')) return '尽调';
        if (text.includes('决策') || text.includes('投资决策')) return '决策';
      }
    }
    
    return '未知';
  }
}

// ============================================================================
// 全局实例
// ============================================================================

const messageMonitor = new MessageMonitor();
const autoInput = new AutoInput();
const completionDetector = new CompletionDetector();

// ============================================================================
// 消息监听 - 与 Background Script 通信
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('📨 收到消息:', request.action);

  if (request.action === 'START_MONITORING') {
    messageMonitor.start();
    sendResponse({ success: true });
  }

  if (request.action === 'STOP_MONITORING') {
    messageMonitor.stop();
    sendResponse({ success: true });
  }

  if (request.action === 'SEND_ANSWER') {
    // 自动输入并发送回答
    // 记录本次回答摘要，避免随后把自己的回答当作新问题
    try {
      messageMonitor.lastAnswerDigest = messageMonitor.simpleDigest(request.answer || '');
    } catch (_) {}

    autoInput.fillTextarea(request.answer)
      .then(() => autoInput.clickSendButton())
      .then(() => {
        sendResponse({ success: true });
        
        // 检查是否完成
        if (completionDetector.isEvaluationComplete()) {
          chrome.runtime.sendMessage({
            action: 'EVALUATION_COMPLETE',
            stage: completionDetector.getCurrentStage()
          });
        }
      })
      .catch(error => {
        console.error('❌ 发送回答失败:', error);
        sendResponse({ success: false, error: error.message });
      });
    
    return true; // 保持消息通道开启
  }

  if (request.action === 'CHECK_COMPLETION') {
    const isComplete = completionDetector.isEvaluationComplete();
    const stage = completionDetector.getCurrentStage();
    sendResponse({ isComplete, stage });
  }
});

console.log('✅ Content Script 初始化完成');
