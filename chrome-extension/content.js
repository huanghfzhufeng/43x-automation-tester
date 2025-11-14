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
    this.pollingInterval = null;  // 新增：轮询定时器
    this.lastMessageCount = 0;
    this.isRunning = false;
    this.messageContainer = null;
    // 🔥 修复：使用数组记录最近的消息摘要，而不是永久记录所有消息
    this.recentDigests = [];  // 只保留最近 5 条消息的摘要
    this.maxRecentDigests = 5;
    // 🔥 修复：记录我们发送的所有回答摘要（用于排除自己的消息）
    this.sentAnswerDigests = new Set();
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
      console.log(`🔔 MutationObserver 触发! 检测到 ${mutations.length} 个变化`);
      mutations.forEach((mutation, i) => {
        console.log(`   变化 ${i+1}: type=${mutation.type}, addedNodes=${mutation.addedNodes.length}, removedNodes=${mutation.removedNodes.length}`);
      });
      this.handleMutations(mutations);
    });

    // 开始监听
    console.log('🔧 配置 MutationObserver...');
    console.log('   监听容器:', this.messageContainer);
    console.log('   容器标签:', this.messageContainer.tagName);
    console.log('   容器类名:', this.messageContainer.className);
    
    this.observer.observe(this.messageContainer, {
      childList: true,
      subtree: true,
      attributes: false,  // 不监听属性变化
      characterData: false  // 不监听文本变化
    });

    console.log('✅ 消息监听已启动');
    
    // 🔥 重要：检查页面上是否已经有消息
    // MutationObserver 只监听新变化，不会检测已存在的内容
    this.checkExistingMessages();
    
    // 🔥 新增：轮询机制，每 2 秒检查一次新消息（防止 MutationObserver 漏掉）
    this.pollingInterval = setInterval(() => {
      console.log('[Polling] 定期检查新消息...');
      this.checkForNewMessages();
    }, 2000);
  }
  
  /**
   * 检查新消息（轮询用）
   * 🔥 修复：基于消息内容而不是数量来检测新消息，支持多轮对话
   */
  async checkForNewMessages() {
    const messages = this.getAllMessages();
    
    console.log(`[Polling] 当前消息数: ${messages.length}, 上次记录: ${this.lastMessageCount}`);
    
    // 🔥 修复：检查最后一条消息是否是新的投资人消息
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const lastMessageText = lastMessage.textContent.trim();
      const lastMessageDigest = this.simpleDigest(lastMessageText);
      
      // 🔥 关键修复：先检查是否已处理过，再检查是否是投资人消息
      if (this.recentDigests.includes(lastMessageDigest)) {
        console.log('[Polling] 最后一条消息已在最近处理过');
      } else if (this.sentAnswerDigests.has(lastMessageDigest)) {
        console.log('[Polling] 最后一条消息是我们发送的回答');
      } else if (this.isInvestorMessage(lastMessage, true)) {
        // skipDuplicateCheck=true，因为我们已经在外部检查过了
        console.log('[Polling] ✅ 发现新的投资人消息!');
        console.log('[Polling] 消息内容:', lastMessageText.substring(0, 100) + '...');
        
        // 添加到最近消息列表
        this.addToRecentDigests(lastMessageDigest);
        
        // 🔥 关键修复：使用 await 等待消息处理完成
        await this.handleNewInvestorMessage(lastMessage);
        
        // 更新计数器
        this.lastMessageCount = messages.length;
        return;
      } else {
        console.log('[Polling] 最后一条不是投资人消息');
      }
    }
    
    // 更新计数器（即使没有新消息也要更新，保持同步）
    if (messages.length !== this.lastMessageCount) {
      console.log(`[Polling] 更新计数器: ${this.lastMessageCount} -> ${messages.length}`);
      this.lastMessageCount = messages.length;
    } else {
      console.log(`[Polling] 无新消息`);
    }
  }
  
  /**
   * 检查页面上已存在的消息
   * 🔥 修复：使用新的去重机制
   */
  checkExistingMessages() {
    console.log('🔍 检查页面上已存在的消息...');
    
    const messages = this.getAllMessages();
    
    if (messages.length > 0) {
      console.log(`✅ 找到 ${messages.length} 个已存在的消息元素`);
      this.lastMessageCount = messages.length;
      
      // 提取最后一条消息
      const lastMessage = messages[messages.length - 1];
      
      // 检查是否是投资人消息（跳过去重检查）
      if (this.isInvestorMessage(lastMessage, true)) {
        const question = this.extractQuestion(lastMessage);
        
        if (question) {
          console.log('📨 检测到已存在的问题:', question.substring(0, 50) + '...');
          const digest = this.simpleDigest(question);
          
          if (!this.recentDigests.includes(digest)) {
            this.addToRecentDigests(digest);
            // 发送到 Background
            chrome.runtime.sendMessage({
              action: 'NEW_QUESTION',
              question: question
            });
          } else {
            console.log('ℹ️ 已存在消息最近已处理过，跳过');
          }
        }
      } else {
        console.log('ℹ️ 最后一条消息不是投资人消息');
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
    
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
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
   * 🔥 修复：改进消息检测逻辑，支持多轮对话
   */
  handleMutations() {
    console.log('[handleMutations] DOM change detected, checking for new messages.');
    
    const messages = this.getAllMessages();
    
    if (messages.length > this.lastMessageCount) {
      console.log(`[handleMutations] ✅ New messages detected! Count: ${messages.length}, Previous: ${this.lastMessageCount}`);
      
      const newMessages = messages.slice(this.lastMessageCount);
      console.log(`[handleMutations] Processing ${newMessages.length} new message(s).`);
      
      // 先更新计数器，避免轮询重复处理
      this.lastMessageCount = messages.length;
      
      newMessages.forEach((newMessage, index) => {
        console.log(`[handleMutations] Checking new message #${index + 1}/${newMessages.length}:`, newMessage.outerHTML.substring(0, 200) + '...');
        
        const messageText = newMessage.textContent.trim();
        const messageDigest = this.simpleDigest(messageText);
        
        // 先检查去重
        if (this.recentDigests.includes(messageDigest)) {
          console.log('[handleMutations] ⏭️ Message already processed recently, skipping.');
          return;
        }
        
        if (this.sentAnswerDigests.has(messageDigest)) {
          console.log('[handleMutations] ⏭️ Message is our sent answer, skipping.');
          return;
        }
        
        // 再检查是否是投资人消息（跳过内部去重检查）
        if (this.isInvestorMessage(newMessage, true)) {
          console.log('[handleMutations] ✅ Investor message found. Handling it.');
          this.addToRecentDigests(messageDigest);
          this.handleNewInvestorMessage(newMessage);
        } else {
          console.log('[handleMutations] ⏭️ Not an investor message, skipping.');
        }
      });
    } else if (messages.length < this.lastMessageCount) {
      console.log(`[handleMutations] ⚠️ Message count decreased. Resetting count from ${this.lastMessageCount} to ${messages.length}.`);
      this.lastMessageCount = messages.length;
    } else {
      console.log('[handleMutations] No new messages.');
    }
  }

  /**
   * 获取所有消息元素
   */
  getAllMessages() {
    // 确保消息容器引用有效
    this.ensureMessageContainer();
    
    if (!this.messageContainer) {
      console.warn('[getAllMessages] ⚠️ 消息容器未初始化');
      return [];
    }
    
    console.log('[getAllMessages] 🔍 开始查找消息元素...');

    // 43X 页面的实际选择器（基于真实 DOM 结构）
    const selectors = [
      // 最精确的选择器：投资人和创业者的消息容器
      '.flex.gap-4.flex-row, .flex.gap-4.flex-row-reverse',
      // 备用选择器
      '[class*="flex gap-4 flex-row"]',
      // 更宽松的选择器
      'main [class*="flex"][class*="gap-4"]'
    ];

    console.log('[getAllMessages] 🔍 开始查找消息元素...');
    
    for (const selector of selectors) {
      const messages = this.messageContainer.querySelectorAll(selector);
      console.log(`[getAllMessages]    尝试选择器 "${selector}": 找到 ${messages.length} 个元素`);
      
      if (messages.length > 0) {
        // 过滤掉明显不是消息的元素
        const validMessages = Array.from(messages).filter(msg => {
          // 必须有文本内容（降低最小长度要求）
          const text = msg.textContent.trim();
          if (!text) return false;
          
          // 不能是输入框容器
          if (msg.querySelector('textarea')) return false;
          
          console.log('[getAllMessages]    Found valid message element with text:', text.substring(0, 80) + '...');
          return true;
        });
        
        if (validMessages.length > 0) {
          console.log(`[getAllMessages] ✅ 使用选择器 "${selector}" 找到 ${validMessages.length} 条有效消息`);
          
          // 打印每条消息的简要信息（用于调试）
          validMessages.forEach((msg, i) => {
            const isInvestor = msg.className.includes('flex-row') && !msg.className.includes('flex-row-reverse');
            const text = msg.textContent.trim().substring(0, 50);
            console.log(`[getAllMessages]   消息 ${i+1}: ${isInvestor ? '投资人' : '创业者'} - ${text}...`);
          });
          
          return validMessages;
        } else {
          console.log(`[getAllMessages]    选择器 "${selector}" 的元素都被过滤掉了`);
        }
      }
    }

    // 如果所有选择器都失败，尝试最宽松的方式
    console.warn('[getAllMessages] ⚠️ 所有选择器都失败，尝试最宽松的方式...');
    const allDivs = this.messageContainer.querySelectorAll('div');
    console.log(`[getAllMessages]    找到 ${allDivs.length} 个 div 元素`);
    
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
      console.log(`[getAllMessages] ✅ 使用 fallback 方式找到 ${fallbackMessages.length} 条消息`);
      return fallbackMessages;
    }

    console.error('[getAllMessages] ❌ 完全未找到任何消息元素');
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
   * 判断是否是投资人的消息（仅检查DOM结构，不检查去重）
   * 🔥 修复：将去重逻辑移到外部，避免循环依赖
   */
  isInvestorMessage(messageElement, skipDuplicateCheck = false) {
    console.log('[isInvestorMessage] Checking element:', messageElement.outerHTML.substring(0, 200) + '...');
    const classList = messageElement.className || '';
    
    // 核心判断：投资人消息是 flex-row，创业者消息是 flex-row-reverse
    if (classList.includes('flex-row-reverse')) {
      console.log('[isInvestorMessage] Result: false (is from entrepreneur - flex-row-reverse). Class: ' + classList);
      return false;
    }
    
    if (!classList.includes('flex-row')) {
      console.log('[isInvestorMessage] Result: false (not a message container). Class: ' + classList);
      return false;
    }

    if (classList.includes('divider')) {
      console.log('[isInvestorMessage] Result: false (is a divider). Class: ' + classList);
      return false;
    }

    const text = messageElement.textContent.trim();
    if (!text || text.length < 10) {
      console.log(`[isInvestorMessage] Result: false (text is too short: "${text}")`);
      return false;
    }

    if (messageElement.querySelector('textarea')) {
      console.log('[isInvestorMessage] Result: false (contains a textarea).');
      return false;
    }

    // 🔥 修复：如果不跳过去重检查，则进行去重检查
    if (!skipDuplicateCheck) {
      const digest = this.simpleDigest(text);
      
      // 检查是否是我们发送的回答
      if (this.sentAnswerDigests.has(digest)) {
        console.log('[isInvestorMessage] Result: false (matches a sent answer digest).');
        return false;
      }
      
      // 检查是否在最近处理过的消息中
      if (this.recentDigests.includes(digest)) {
          console.log('[isInvestorMessage] Result: false (message has been recently processed).');
          return false;
      }
    }

    console.log('[isInvestorMessage] Result: true. This is a new investor message.');
    return true;
  }

  /**
   * 处理新的投资人消息
   * 🔥 修复：不再在这里做去重检查，因为调用前已经检查过了
   */
  async handleNewInvestorMessage(messageElement) {
    console.log('💬 收到投资人消息');

    // 等待消息完全加载（thinking 状态结束）
    await this.waitForMessageComplete(messageElement);

    // 提取问题文本
    const question = this.extractQuestion(messageElement);

    console.log('⚠️⚠️⚠️ 提取结果详情:');
    console.log('  - 问题内容:', `[${question}]`);
    console.log('  - 问题长度:', question ? question.length : 0);
    console.log('  - 是否为空:', !question || question.trim() === '');
    console.log('  - 消息元素HTML:', messageElement.outerHTML.substring(0, 500));

    if (question) {
      console.log(`📝 提取到问题: ${question.substring(0, 100)}...`);

      // 发送给 Background Script
      console.log('⚠️ 即将发送 NEW_QUESTION 到 Background');
      chrome.runtime.sendMessage({
        action: 'NEW_QUESTION',
        question: question
      });
      console.log('✅ NEW_QUESTION 已发送');
    } else {
      console.warn('⚠️ 未能提取到问题文本');
    }
  }
  
  /**
   * 🔥 新增：添加消息摘要到最近列表
   */
  addToRecentDigests(digest) {
    this.recentDigests.push(digest);
    // 保持列表大小，只保留最近的 N 条
    if (this.recentDigests.length > this.maxRecentDigests) {
      this.recentDigests.shift();  // 移除最旧的
    }
    console.log(`[addToRecentDigests] 当前最近消息数: ${this.recentDigests.length}`);
  }

  /**
   * 等待消息完全加载
   * 改进：检查文本内容而不是 DOM 属性
   */
  async waitForMessageComplete(messageElement) {
    const maxWait = 60000; // 最多等待 60 秒
    const checkInterval = 500; // 每 500ms 检查一次
    let waited = 0;
    
    console.log('[waitForMessageComplete] 开始等待消息完成...');

    while (waited < maxWait) {
      const text = messageElement.textContent.trim();
      
      // 检查是否还在思考状态（多种可能的文本）
      const isThinking = 
        text.includes('思考中') ||
        text.includes('思考准备') ||
        text.includes('正在思考') ||
        text.includes('thinking') ||
        text.includes('Thinking') ||
        text.length < 20;  // 文本太短，可能还没生成完
      
      // 检查 DOM 属性
      const thinkingElement = messageElement.querySelector('[data-status="thinking"]');
      
      if (!isThinking && !thinkingElement) {
        console.log('[waitForMessageComplete] ✅ 消息加载完成');
        console.log('[waitForMessageComplete] 最终文本长度:', text.length);
        console.log('[waitForMessageComplete] 最终文本预览:', text.substring(0, 100) + '...');
        return;
      }
      
      console.log(`[waitForMessageComplete] 等待中... (${waited}ms) 当前文本: ${text.substring(0, 50)}...`);
      await this.sleep(checkInterval);
      waited += checkInterval;
    }

    console.warn('[waitForMessageComplete] ⚠️ 等待消息完成超时');
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
   * 基于 43X 真实 DOM 结构：
   * - 投资人消息文本在 .wrap-anywhere.max-w-240.text-primary 中
   * - 需要移除"思考准备了 X 秒钟"这类文本
   * - 需要移除名字（孙悟空）
   */
  extractQuestion(messageElement) {
    // 克隆元素以避免修改原始 DOM
    const clonedElement = messageElement.cloneNode(true);
    
    // 移除头像
    const avatars = clonedElement.querySelectorAll('[class*="Avatar"]');
    avatars.forEach(avatar => avatar.remove());
    
    // 移除按钮
    const buttons = clonedElement.querySelectorAll('button');
    buttons.forEach(button => button.remove());
    
    // 查找文本内容容器（投资人消息的文本在这个 class 中）
    const textContainer = clonedElement.querySelector('.wrap-anywhere.max-w-240.text-primary');
    
    if (textContainer) {
      let text = textContainer.textContent.trim();
      
      // 移除"思考准备了 X 秒钟"这类文本
      text = text.replace(/思考准备了\s*\d+\s*秒钟/g, '');
      
      // 移除名字（孙悟空、朱锋等）
      text = text.replace(/^(孙悟空|朱锋)[，,\s]*/g, '');
      
      // 清理多余空白
      text = text.trim();
      
      if (text && text.length > 10) {
        console.log('📝 提取到文本 (精确匹配):', text.substring(0, 100) + '...');
        return text;
      }
    }
    
    // 备用方案：获取所有文本
    let text = clonedElement.textContent.trim();
    
    // 移除"思考准备了 X 秒钟"
    text = text.replace(/思考准备了\s*\d+\s*秒钟/g, '');
    
    // 移除名字
    text = text.replace(/^(孙悟空|朱锋)[，,\s]*/g, '');
    
    // 清理多余空白
    text = text.trim();
    
    if (text && text.length > 10) {
      console.log('📝 提取到文本 (fallback):', text.substring(0, 100) + '...');
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
      
      // 检查是否是最终阶段 (更严格的关键词)
      if (text.includes('投资决策') || text.includes('最终决策') || text.includes('评估完成')) {
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
          if (text && (text.includes('投资决策') || text.includes('评估完成'))) {
            console.log('✅ 检测到评估完成（虚线分隔符）:', text);
            return true;
          }
          sibling = sibling.nextElementSibling;
        }
      }
    }

    // 方法 3: 检测消息内容关键词 (更严格的关键词)
    const messages = document.querySelectorAll('[class*="flex"][class*="gap-4"]');
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      const text = lastMessage.textContent;
      
      if (text.includes('评估完成') || text.includes('决策完成') || text.includes('投资决策') || text.includes('感谢您的参与')) {
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
    // 🔥 修复：记录本次回答摘要到集合中，避免把自己的回答当作新问题
    try {
      const answerDigest = messageMonitor.simpleDigest(request.answer || '');
      messageMonitor.sentAnswerDigests.add(answerDigest);
      console.log(`[SEND_ANSWER] 记录回答摘要: ${answerDigest}`);
      
      // 🔥 修复：限制集合大小，只保留最近的 10 条回答
      if (messageMonitor.sentAnswerDigests.size > 10) {
        const firstDigest = messageMonitor.sentAnswerDigests.values().next().value;
        messageMonitor.sentAnswerDigests.delete(firstDigest);
      }
    } catch (e) {
      console.error('记录回答摘要失败:', e);
    }

    autoInput.fillTextarea(request.answer)
      .then(() => autoInput.clickSendButton())
      .then(() => {
        sendResponse({ success: true });
        
        // 暂时禁用自动完成检测
        /*
        if (completionDetector.isEvaluationComplete()) {
          chrome.runtime.sendMessage({
            action: 'EVALUATION_COMPLETE',
            stage: completionDetector.getCurrentStage()
          });
        }
        */
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
