/**
 * Popup UI - 43X Agent Tester
 * 
 * 负责用户界面交互和状态显示
 */

console.log('🚀 Popup UI 已加载');

// ============================================================================
// 全局状态
// ============================================================================

let currentConfig = null;
let uploadedFiles = {};
let isTestRunning = false;
let timerInterval = null;
let startTime = null;

// ============================================================================
// DOM 元素
// ============================================================================

const elements = {
  // 表单配置
  configForm: document.getElementById('configForm'),
  scenarioName: document.getElementById('scenarioName'),
  companyName: document.getElementById('companyName'),
  industry: document.getElementById('industry'),
  product: document.getElementById('product'),
  revenue: document.getElementById('revenue'),
  team: document.getElementById('team'),
  fundingNeed: document.getElementById('fundingNeed'),
  expectedResult: document.getElementById('expectedResult'),
  customers: document.getElementById('customers'),
  technology: document.getElementById('technology'),
  toggleAdvanced: document.getElementById('toggleAdvanced'),
  advancedIcon: document.getElementById('advancedIcon'),
  advancedOptions: document.getElementById('advancedOptions'),
  configPreview: document.getElementById('configPreview'),
  previewContent: document.getElementById('previewContent'),
  editConfig: document.getElementById('editConfig'),
  
  // 上传
  uploadFilesBtn: document.getElementById('uploadFilesBtn'),
  filesInput: document.getElementById('filesInput'),
  fileList: document.getElementById('fileList'),
  aiExtractStatus: document.getElementById('aiExtractStatus'),
  aiExtractSuccess: document.getElementById('aiExtractSuccess'),
  aiSuccessMessage: document.getElementById('aiSuccessMessage'),
  
  // 场景选择
  recentScenarios: document.getElementById('recentScenarios'),
  
  // 控制
  startTest: document.getElementById('startTest'),
  stopTest: document.getElementById('stopTest'),
  
  // 进度
  progressSection: document.getElementById('progressSection'),
  statusBadge: document.getElementById('statusBadge'),
  rounds: document.getElementById('rounds'),
  stage: document.getElementById('stage'),
  timer: document.getElementById('timer'),
  progressBar: document.getElementById('progressBar'),
  
  // 结果
  resultSection: document.getElementById('resultSection'),
  resultIcon: document.getElementById('resultIcon'),
  resultDetails: document.getElementById('resultDetails'),
  
  // 操作
  viewLogs: document.getElementById('viewLogs'),
  settings: document.getElementById('settings'),
  
  // 状态
  serviceStatus: document.getElementById('serviceStatus')
};

// ============================================================================
// 初始化
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('📋 初始化 Popup UI');
  
  // 加载配置
  await loadSettings();
  
  // 绑定事件
  bindEvents();
  
  // 加载最近使用的场景
  loadRecentScenarios();
  
  // 检查服务状态
  checkServiceStatus();
  
  // 监听来自 Background 的消息
  chrome.runtime.onMessage.addListener(handleBackgroundMessage);
});

// ============================================================================
// 配置加载
// ============================================================================

let currentSettings = null;

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
    
    console.log('✅ 配置已加载:', currentSettings);
    
  } catch (error) {
    console.error('❌ 加载配置失败:', error);
  }
}

// ============================================================================
// 事件绑定
// ============================================================================

function bindEvents() {
  // 表单提交
  elements.configForm.addEventListener('submit', handleFormSubmit);
  
  // 高级选项切换
  elements.toggleAdvanced.addEventListener('click', toggleAdvancedOptions);
  
  // 编辑配置
  elements.editConfig.addEventListener('click', handleEditConfig);
  
  // 上传文件（自动触发 AI 提取）
  elements.uploadFilesBtn.addEventListener('click', () => {
    elements.filesInput.click();
  });
  
  elements.filesInput.addEventListener('change', handleFilesUploadWithAI);
  
  // 场景选择
  elements.recentScenarios.addEventListener('change', handleScenarioSelect);
  
  // 控制按钮
  elements.startTest.addEventListener('click', handleStartTest);
  elements.stopTest.addEventListener('click', handleStopTest);
  
  // 操作按钮
  elements.viewLogs.addEventListener('click', handleViewLogs);
  elements.settings.addEventListener('click', handleOpenSettings);
  
  // 拖拽上传
  setupDragAndDrop();
}

// ============================================================================
// 拖拽上传
// ============================================================================

function setupDragAndDrop() {
  // 拖拽上传功能已移除
}

// ============================================================================
// 表单处理
// ============================================================================

function handleFormSubmit(event) {
  event.preventDefault();
  
  // 收集表单数据
  const formData = {
    scenario_name: elements.scenarioName.value.trim(),
    company_name: elements.companyName.value.trim(),
    industry: elements.industry.value || undefined,
    product: elements.product.value.trim() || undefined,
    revenue: elements.revenue.value.trim() || undefined,
    team: elements.team.value.trim() || undefined,
    funding_need: elements.fundingNeed.value.trim() || undefined,
    expected_result: elements.expectedResult.value || undefined,
  };
  
  // 处理客户案例（逗号分隔）
  const customersInput = elements.customers.value.trim();
  if (customersInput) {
    formData.customers = customersInput.split(',').map(c => c.trim()).filter(c => c);
  }
  
  // 处理技术描述
  const technologyInput = elements.technology.value.trim();
  if (technologyInput) {
    formData.technology = technologyInput;
  }
  
  // 移除 undefined 字段
  Object.keys(formData).forEach(key => {
    if (formData[key] === undefined) {
      delete formData[key];
    }
  });
  
  // 保存配置
  currentConfig = formData;
  
  // 显示预览
  showConfigPreview(formData);
  
  // 启用开始按钮
  updateStartButton();
  
  // 保存到最近使用
  saveToRecent(formData);
  
  console.log('✅ 配置已生成:', formData);
  showToast('配置已生成！');
}

function showConfigPreview(config) {
  // 隐藏表单，显示预览
  elements.configForm.style.display = 'none';
  elements.configPreview.style.display = 'block';
  
  // 生成预览内容
  let html = '';
  
  html += `<div class="preview-item"><span class="preview-label">场景名称:</span> ${config.scenario_name}</div>`;
  html += `<div class="preview-item"><span class="preview-label">公司名称:</span> ${config.company_name}</div>`;
  
  if (config.industry) {
    html += `<div class="preview-item"><span class="preview-label">行业:</span> ${config.industry}</div>`;
  }
  
  if (config.product) {
    html += `<div class="preview-item"><span class="preview-label">产品:</span> ${config.product}</div>`;
  }
  
  if (config.revenue) {
    html += `<div class="preview-item"><span class="preview-label">营收:</span> ${config.revenue}</div>`;
  }
  
  if (config.team) {
    html += `<div class="preview-item"><span class="preview-label">团队:</span> ${config.team}</div>`;
  }
  
  if (config.funding_need) {
    html += `<div class="preview-item"><span class="preview-label">融资需求:</span> ${config.funding_need}</div>`;
  }
  
  if (config.customers && config.customers.length > 0) {
    html += `<div class="preview-item"><span class="preview-label">客户:</span> ${config.customers.join(', ')}</div>`;
  }
  
  if (config.technology) {
    html += `<div class="preview-item"><span class="preview-label">技术:</span> ${config.technology}</div>`;
  }
  
  if (config.expected_result) {
    const resultText = config.expected_result === 'passed' ? '通过' : '拒绝';
    html += `<div class="preview-item"><span class="preview-label">预期结果:</span> ${resultText}</div>`;
  }
  
  elements.previewContent.innerHTML = html;
}

function handleEditConfig() {
  // 显示表单，隐藏预览
  elements.configForm.style.display = 'block';
  elements.configPreview.style.display = 'none';
}

function toggleAdvancedOptions() {
  const isVisible = elements.advancedOptions.style.display !== 'none';
  
  if (isVisible) {
    elements.advancedOptions.style.display = 'none';
    elements.advancedIcon.classList.remove('expanded');
  } else {
    elements.advancedOptions.style.display = 'block';
    elements.advancedIcon.classList.add('expanded');
  }
}

// ============================================================================
// 文件上传处理（自动触发 AI 提取）
// ============================================================================

async function handleFilesUploadWithAI(event) {
  const files = Array.from(event.target.files);
  if (files.length === 0) return;
  
  console.log('📁 智能上传文件:', files.length, '个');
  
  // 显示加载状态
  elements.aiExtractStatus.style.display = 'flex';
  elements.aiExtractSuccess.style.display = 'none';
  
  let successCount = 0;
  let failCount = 0;
  
  for (const file of files) {
    try {
      // 验证文件类型
      const validTypes = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.md', '.txt'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      if (!validTypes.includes(fileExt)) {
        throw new Error(`不支持的文件类型: ${fileExt}`);
      }
      
      // 验证文件大小（最大 10MB）
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        throw new Error(`文件过大（最大 10MB）`);
      }
      
      // 读取文件内容
      let content;
      if (fileExt === '.pdf' || fileExt === '.docx' || fileExt === '.doc' || fileExt === '.pptx' || fileExt === '.ppt') {
        content = await readFileAsBase64(file);
      } else {
        content = await file.text();
      }
      
      uploadedFiles[file.name] = {
        content: content,
        type: file.type,
        size: file.size,
        extension: fileExt
      };
      
      // 显示文件
      addFileToList(file.name, file.size, 'file');
      
      successCount++;
      console.log('✅ 文件加载成功:', file.name);
      
    } catch (error) {
      failCount++;
      console.error('❌ 文件加载失败:', file.name, error);
      alert(`文件 "${file.name}" 加载失败: ${error.message}`);
    }
  }
  
  // 如果有文件上传成功，调用AI提取
  if (successCount > 0) {
    await extractInfoWithAI();
  } else {
    elements.aiExtractStatus.style.display = 'none';
  }
  
  // 清空 input
  event.target.value = '';
}

async function extractInfoWithAI() {
  try {
    console.log('🤖 开始AI提取信息...');
    console.log('📦 已上传文件数:', Object.keys(uploadedFiles).length);
    
    // 准备文件内容
    const filesContent = {};
    for (const [filename, fileData] of Object.entries(uploadedFiles)) {
      filesContent[filename] = fileData.content || fileData;
      console.log(`   - ${filename}: ${typeof filesContent[filename] === 'string' ? filesContent[filename].length : 'unknown'} 字符`);
    }
    
    // 调用后端API进行AI提取
    const serviceUrl = currentSettings?.agentServiceUrl || 'http://localhost:8001';
    console.log('🌐 API地址:', `${serviceUrl}/api/extract/info`);
    
    const response = await fetch(`${serviceUrl}/api/extract/info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        files_content: filesContent
      }),
      signal: AbortSignal.timeout(60000) // 60秒超时
    });
    
    console.log('📡 API响应状态:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ API错误响应:', errorText);
      throw new Error(`API请求失败: ${response.status} - ${errorText.substring(0, 200)}`);
    }
    
    const result = await response.json();
    
    console.log('✅ AI提取成功:', result);
    
    // 隐藏加载状态
    elements.aiExtractStatus.style.display = 'none';
    
    // 自动填充表单
    const filledCount = fillFormWithExtractedInfo(result.extracted_info);
    
    // 显示成功提示
    if (filledCount > 0) {
      elements.aiSuccessMessage.textContent = `已自动填充 ${filledCount} 个字段，请检查并补充`;
      elements.aiExtractSuccess.style.display = 'flex';
      
      // 5秒后自动隐藏
      setTimeout(() => {
        elements.aiExtractSuccess.style.display = 'none';
      }, 5000);
    } else {
      // 没有提取到信息
      elements.aiExtractStatus.style.display = 'none';
      showToast('⚠️ 未能提取到信息，请手动填写表单', 3000);
    }
    
  } catch (error) {
    console.error('❌ AI提取失败:', error);
    console.error('   错误详情:', error.message);
    console.error('   错误堆栈:', error.stack);
    
    // 隐藏加载状态
    elements.aiExtractStatus.style.display = 'none';
    
    // 显示详细错误提示
    const errorMsg = error.message || '未知错误';
    showToast(`⚠️ AI提取失败: ${errorMsg.substring(0, 50)}`, 5000);
    
    // 同时在控制台显示完整错误
    alert(`AI提取失败\n\n错误信息：${errorMsg}\n\n请检查：\n1. Agent Service 是否运行（http://localhost:8001）\n2. 浏览器控制台是否有更多错误信息`);
  }
}

function fillFormWithExtractedInfo(info) {
  let filledCount = 0;
  
  // 自动生成场景名称
  if (info.company_name && info.product) {
    elements.scenarioName.value = `${info.company_name}_${info.product.substring(0, 20)}`;
    elements.scenarioName.classList.add('auto-filled');
    elements.scenarioName.parentElement.classList.add('auto-filled');
    filledCount++;
  } else if (info.company_name) {
    elements.scenarioName.value = `${info.company_name}_测试`;
    elements.scenarioName.classList.add('auto-filled');
    elements.scenarioName.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  // 填充基础字段并标记
  if (info.company_name) {
    elements.companyName.value = info.company_name;
    elements.companyName.classList.add('auto-filled');
    elements.companyName.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  if (info.industry) {
    elements.industry.value = info.industry;
    elements.industry.classList.add('auto-filled');
    elements.industry.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  if (info.product) {
    elements.product.value = info.product;
    elements.product.classList.add('auto-filled');
    elements.product.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  if (info.revenue) {
    elements.revenue.value = info.revenue;
    elements.revenue.classList.add('auto-filled');
    elements.revenue.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  if (info.team) {
    elements.team.value = info.team;
    elements.team.classList.add('auto-filled');
    elements.team.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  if (info.funding_need) {
    elements.fundingNeed.value = info.funding_need;
    elements.fundingNeed.classList.add('auto-filled');
    elements.fundingNeed.parentElement.classList.add('auto-filled');
    filledCount++;
  }
  
  // 填充高级字段
  if (info.customers && Array.isArray(info.customers)) {
    elements.customers.value = info.customers.join(', ');
    elements.customers.classList.add('auto-filled');
    elements.customers.parentElement.classList.add('auto-filled');
    filledCount++;
    // 展开高级选项
    elements.advancedOptions.style.display = 'block';
    elements.advancedIcon.classList.add('expanded');
  }
  
  if (info.technology) {
    elements.technology.value = info.technology;
    elements.technology.classList.add('auto-filled');
    elements.technology.parentElement.classList.add('auto-filled');
    filledCount++;
    // 展开高级选项
    elements.advancedOptions.style.display = 'block';
    elements.advancedIcon.classList.add('expanded');
  }
  
  console.log(`✅ 表单已自动填充 ${filledCount} 个字段`);
  
  return filledCount;
}

// ============================================================================
// 旧的文件上传处理（已废弃，保留兼容性）
// ============================================================================

async function handleFilesUpload(event) {
  const files = Array.from(event.target.files);
  if (files.length === 0) return;
  
  console.log('📁 上传文件:', files.length, '个');
  
  let successCount = 0;
  let failCount = 0;
  const errors = [];
  
  for (const file of files) {
    try {
      // 验证文件类型
      const validTypes = ['.pdf', '.docx', '.doc', '.pptx', '.ppt', '.md', '.txt'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      if (!validTypes.includes(fileExt)) {
        throw new Error(`不支持的文件类型: ${fileExt}`);
      }
      
      // 验证文件大小（最大 10MB）
      const maxSize = 10 * 1024 * 1024;
      if (file.size > maxSize) {
        throw new Error(`文件过大（最大 10MB）`);
      }
      
      // 检查是否已存在
      if (uploadedFiles[file.name]) {
        const overwrite = confirm(`文件 "${file.name}" 已存在，是否覆盖？`);
        if (!overwrite) {
          console.log('⏭️ 跳过文件:', file.name);
          continue;
        }
        // 移除旧的显示
        const oldItem = elements.fileList.querySelector(`[data-filename="${file.name}"][data-type="file"]`);
        if (oldItem) oldItem.remove();
      }
      
      // 读取文件内容
      let content;
      if (fileExt === '.pdf' || fileExt === '.docx' || fileExt === '.doc' || fileExt === '.pptx' || fileExt === '.ppt') {
        // 对于二进制文件，读取为 base64
        content = await readFileAsBase64(file);
      } else {
        // 对于文本文件，读取为文本
        content = await file.text();
      }
      
      uploadedFiles[file.name] = {
        content: content,
        type: file.type,
        size: file.size,
        extension: fileExt
      };
      
      // 显示文件
      addFileToList(file.name, file.size, 'file');
      
      successCount++;
      console.log('✅ 文件加载成功:', file.name);
      
    } catch (error) {
      failCount++;
      errors.push(`${file.name}: ${error.message}`);
      console.error('❌ 文件加载失败:', file.name, error);
    }
  }
  
  // 显示结果摘要
  if (successCount > 0 || failCount > 0) {
    let message = '';
    if (successCount > 0) {
      message += `成功上传 ${successCount} 个文件`;
    }
    if (failCount > 0) {
      message += (message ? '\n' : '') + `失败 ${failCount} 个文件`;
      if (errors.length > 0) {
        message += '\n\n错误详情:\n' + errors.join('\n');
      }
    }
    alert(message);
  }
  
  // 清空 input，允许重复上传同一文件
  event.target.value = '';
}

// 读取文件为 Base64
function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function addFileToList(filename, size, type, targetList = null) {
  // 确定目标列表
  const fileList = targetList || elements.fileList;
  
  // 检查是否已存在（避免重复显示）
  const existing = fileList.querySelector(`[data-filename="${escapeHtml(filename)}"]`);
  if (existing) {
    existing.remove();
  }
  
  const fileItem = document.createElement('div');
  fileItem.className = 'file-item';
  fileItem.dataset.filename = filename;
  fileItem.dataset.type = type;
  
  const icon = getFileIcon(filename);
  const sizeText = formatFileSize(size);
  
  // 创建文件名元素
  const fileNameSpan = document.createElement('span');
  fileNameSpan.className = 'file-name';
  fileNameSpan.textContent = `${icon} ${filename}`;
  fileNameSpan.title = filename; // 鼠标悬停显示完整文件名
  
  // 创建文件大小元素
  const fileSizeSpan = document.createElement('span');
  fileSizeSpan.className = 'file-size';
  fileSizeSpan.textContent = sizeText;
  
  // 创建删除按钮
  const removeButton = document.createElement('button');
  removeButton.className = 'file-remove';
  removeButton.textContent = '✕';
  removeButton.title = '删除文件';
  removeButton.addEventListener('click', () => removeFile(filename, type));
  
  // 组装元素
  fileItem.appendChild(fileNameSpan);
  fileItem.appendChild(fileSizeSpan);
  fileItem.appendChild(removeButton);
  
  // 添加到列表
  fileList.appendChild(fileItem);
  
  console.log(`📎 添加文件到列表: ${filename} (${type})`);
}

function removeFile(filename, type) {
  // 确认删除
  const confirmDelete = confirm(`确定要删除 "${filename}" 吗？`);
  if (!confirmDelete) {
    return;
  }
  
  // 从列表中移除
  const fileItem = elements.fileList.querySelector(`[data-filename="${escapeHtml(filename)}"]`);
  if (fileItem) fileItem.remove();
  
  // 从状态移除
  delete uploadedFiles[filename];
  console.log('🗑️ 移除资料文件:', filename);
  
  // 显示提示
  showToast(`已删除: ${filename}`);
}

// 根据文件扩展名返回图标
function getFileIcon(filename) {
  const ext = filename.substring(filename.lastIndexOf('.')).toLowerCase();
  const iconMap = {
    '.pdf': '📕',
    '.docx': '📘',
    '.doc': '📘',
    '.pptx': '📊',
    '.ppt': '📊',
    '.md': '📝',
    '.txt': '📄'
  };
  return iconMap[ext] || '📄';
}

// HTML 转义（防止 XSS）
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// 显示临时提示
function showToast(message, duration = 2000) {
  // 创建 toast 元素
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 12px 24px;
    border-radius: 6px;
    font-size: 13px;
    z-index: 10000;
    animation: fadeIn 0.3s;
  `;
  
  document.body.appendChild(toast);
  
  // 自动移除
  setTimeout(() => {
    toast.style.animation = 'fadeOut 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ============================================================================
// 场景管理
// ============================================================================

async function loadRecentScenarios() {
  try {
    const result = await chrome.storage.local.get('recentScenarios');
    const scenarios = result.recentScenarios || [];
    
    elements.recentScenarios.innerHTML = '<option value="">选择最近使用的场景...</option>';
    
    scenarios.forEach((scenario, index) => {
      const option = document.createElement('option');
      option.value = index;
      
      // 格式化时间
      const date = new Date(scenario.timestamp);
      const timeStr = formatRelativeTime(scenario.timestamp);
      
      // 统计文件数量
      const fileCount = Object.keys(scenario.files || {}).length;
      const fileInfo = fileCount > 0 ? ` (${fileCount}个文件)` : '';
      
      option.textContent = `${scenario.config.scenario_name} - ${scenario.config.company_name}${fileInfo} - ${timeStr}`;
      option.title = `场景: ${scenario.config.scenario_name}\n公司: ${scenario.config.company_name}\n文件: ${fileCount}个\n时间: ${date.toLocaleString('zh-CN')}`;
      
      elements.recentScenarios.appendChild(option);
    });
    
    console.log('📋 加载最近场景:', scenarios.length, '个');
    
  } catch (error) {
    console.error('❌ 加载最近场景失败:', error);
  }
}

// 格式化相对时间
function formatRelativeTime(timestamp) {
  const now = Date.now();
  const diff = now - timestamp;
  
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  
  if (diff < minute) {
    return '刚刚';
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`;
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`;
  } else if (diff < 7 * day) {
    return `${Math.floor(diff / day)}天前`;
  } else {
    const date = new Date(timestamp);
    return date.toLocaleDateString('zh-CN');
  }
}

async function handleScenarioSelect(event) {
  const index = event.target.value;
  if (!index) return;
  
  try {
    const result = await chrome.storage.local.get('recentScenarios');
    const scenarios = result.recentScenarios || [];
    const scenario = scenarios[parseInt(index)];
    
    if (!scenario) {
      alert('场景不存在');
      return;
    }
    
    // 确认加载
    const confirmLoad = confirm(`加载场景 "${scenario.config.scenario_name}"？\n当前未保存的配置将被覆盖。`);
    if (!confirmLoad) {
      // 重置下拉菜单
      elements.recentScenarios.value = '';
      return;
    }
    
    // 加载配置
    currentConfig = scenario.config;
    uploadedFiles = scenario.files || {};
    
    // 加载到表单
    loadConfigToForm(scenario.config);
    
    // 清空文件列表并重新加载
    elements.fileList.innerHTML = '';
    Object.entries(uploadedFiles).forEach(([filename, fileData]) => {
      let size = 0;
      if (typeof fileData === 'string') {
        size = fileData.length;
      } else if (fileData && fileData.content) {
        size = fileData.size || fileData.content.length;
      }
      addFileToList(filename, size, 'file', elements.fileList);
    });
    
    // 显示预览
    showConfigPreview(scenario.config);
    
    updateStartButton();
    
    console.log('✅ 加载场景:', scenario.config.scenario_name);
    showToast(`已加载场景: ${scenario.config.scenario_name}`);
    
  } catch (error) {
    console.error('❌ 加载场景失败:', error);
    alert(`加载场景失败: ${error.message}`);
  }
}

function loadConfigToForm(config) {
  // 填充表单字段
  elements.scenarioName.value = config.scenario_name || '';
  elements.companyName.value = config.company_name || '';
  elements.industry.value = config.industry || '';
  elements.product.value = config.product || '';
  elements.revenue.value = config.revenue || '';
  elements.team.value = config.team || '';
  elements.fundingNeed.value = config.funding_need || '';
  elements.expectedResult.value = config.expected_result || '';
  
  // 处理客户案例
  if (config.customers && Array.isArray(config.customers)) {
    elements.customers.value = config.customers.join(', ');
  } else {
    elements.customers.value = '';
  }
  
  // 处理技术描述
  elements.technology.value = config.technology || '';
  
  // 如果有高级字段，展开高级选项
  if (config.expected_result || config.customers || config.technology) {
    elements.advancedOptions.style.display = 'block';
    elements.advancedIcon.classList.add('expanded');
  }
}

async function saveToRecent(config) {
  try {
    const result = await chrome.storage.local.get('recentScenarios');
    let scenarios = result.recentScenarios || [];
    
    // 添加到列表开头
    scenarios.unshift({
      config: config,
      files: uploadedFiles,
      timestamp: Date.now()
    });
    
    // 只保留最近 5 个
    scenarios = scenarios.slice(0, 5);
    
    await chrome.storage.local.set({ recentScenarios: scenarios });
    
    // 重新加载列表
    await loadRecentScenarios();
    
  } catch (error) {
    console.error('❌ 保存场景失败:', error);
  }
}

// ============================================================================
// 测试控制
// ============================================================================

async function handleStartTest() {
  if (!currentConfig) {
    alert('请先上传场景配置文件');
    return;
  }
  
  // 查找所有 43X 页面
  const validUrls = [
    'localhost:3000',
    '43x.ai',
    'www-dev-74d2c2a9.zenia.art'
  ];
  
  // 获取所有标签页
  const allTabs = await chrome.tabs.query({});
  const x43Tabs = allTabs.filter(tab => 
    tab.url && validUrls.some(url => tab.url.includes(url))
  );
  
  if (x43Tabs.length === 0) {
    alert('未找到 43X 对话页面\n\n请先打开以下页面之一：\n- localhost:3000\n- 43x.ai\n- www-dev-74d2c2a9.zenia.art');
    return;
  }
  
  // 使用第一个找到的 43X 页面
  const currentTab = x43Tabs[0];
  
  console.log('✅ 找到 43X 页面:', currentTab.url);
  
  // 如果有多个 43X 页面，提示用户
  if (x43Tabs.length > 1) {
    console.log(`ℹ️ 找到 ${x43Tabs.length} 个 43X 页面，使用第一个`);
  }
  
  console.log('🚀 开始测试');
  
  // 更新 UI
  isTestRunning = true;
  updateButtons();
  showProgress();
  updateStatus('running', '运行中');
  
  // 启动计时器
  startTimer();
  
  // 发送消息到 Background
  // 处理 filesContent：转换为 Python API 期望的格式
  let filesContent = null;
  if (Object.keys(uploadedFiles).length > 0) {
    filesContent = {};
    for (const [filename, fileData] of Object.entries(uploadedFiles)) {
      // Python API 期望的是 {filename: content_string}
      filesContent[filename] = fileData.content || fileData;
    }
  }
  
  chrome.runtime.sendMessage({
    action: 'START_TEST',
    scenarioConfig: currentConfig,
    filesContent: filesContent,
    tabId: currentTab.id
  }, (response) => {
    if (response && response.success) {
      console.log('✅ 测试启动成功');
    } else {
      console.error('❌ 测试启动失败:', response?.error);
      alert(`测试启动失败: ${response?.error || '未知错误'}`);
      handleStopTest();
    }
  });
}

async function handleStopTest() {
  console.log('🛑 停止测试');
  
  // 发送消息到 Background
  chrome.runtime.sendMessage({
    action: 'STOP_TEST'
  }, (response) => {
    if (response && response.success) {
      console.log('✅ 测试已停止');
    }
  });
  
  // 更新 UI
  isTestRunning = false;
  updateButtons();
  stopTimer();
  updateStatus('waiting', '已停止');
}

// ============================================================================
// UI 更新
// ============================================================================

function updateStartButton() {
  elements.startTest.disabled = !currentConfig || isTestRunning;
}

function updateButtons() {
  elements.startTest.disabled = isTestRunning || !currentConfig;
  elements.stopTest.disabled = !isTestRunning;
}

function showProgress() {
  elements.progressSection.style.display = 'block';
  elements.resultSection.style.display = 'none';
}

function showResult(icon, details) {
  elements.progressSection.style.display = 'none';
  elements.resultSection.style.display = 'block';
  elements.resultIcon.textContent = icon;
  elements.resultDetails.innerHTML = details;
}

function updateStatus(status, text) {
  elements.statusBadge.className = `status-badge ${status}`;
  elements.statusBadge.textContent = text;
}

function updateProgress(data) {
  // 更新轮次
  elements.rounds.textContent = `${data.rounds || 0} / 50`;
  
  // 更新进度条
  const progress = Math.min((data.rounds || 0) / 50 * 100, 100);
  elements.progressBar.style.width = progress + '%';
}

// ============================================================================
// 计时器
// ============================================================================

function startTimer() {
  startTime = Date.now();
  timerInterval = setInterval(updateTimer, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function updateTimer() {
  if (!startTime) return;
  
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  
  elements.timer.textContent = 
    `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// ============================================================================
// Background 消息处理
// ============================================================================

function handleBackgroundMessage(request, sender, sendResponse) {
  if (request.action === 'UPDATE_STATUS') {
    console.log('📨 收到状态更新:', request.type);
    
    switch (request.type) {
      case 'PROGRESS':
        updateProgress(request.data);
        break;
        
      case 'COMPLETED':
        handleTestComplete(request.data);
        break;
        
      case 'STOPPED':
        handleTestStopped(request.data);
        break;
        
      case 'ERROR':
        handleTestError(request.data);
        break;
    }
  }
}

function handleTestComplete(data) {
  console.log('🎉 测试完成:', data);
  
  isTestRunning = false;
  updateButtons();
  stopTimer();
  
  const details = `
    <p><strong>测试完成！</strong></p>
    <p>总轮次: ${data.stats.rounds}</p>
    <p>总耗时: ${formatTime(data.stats.elapsed)}</p>
    <p>最终阶段: ${data.stage}</p>
  `;
  
  showResult('✅', details);
}

function handleTestStopped(data) {
  console.log('🛑 测试已停止:', data);
  
  isTestRunning = false;
  updateButtons();
  stopTimer();
  updateStatus('waiting', '已停止');
}

function handleTestError(data) {
  console.error('❌ 测试错误:', data);
  
  alert(`测试错误 (Round ${data.round}): ${data.message}`);
}

// ============================================================================
// 服务状态检查
// ============================================================================

async function checkServiceStatus() {
  try {
    const serviceUrl = currentSettings?.agentServiceUrl || 'http://localhost:8001';
    const response = await fetch(`${serviceUrl}/health`, {
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      elements.serviceStatus.textContent = '🟢 Agent Service 已连接';
      elements.serviceStatus.className = 'service-status connected';
    } else {
      throw new Error('Service unavailable');
    }
  } catch (error) {
    elements.serviceStatus.textContent = '🔴 Agent Service 未连接';
    elements.serviceStatus.className = 'service-status disconnected';
  }
  
  // 每 10 秒检查一次
  setTimeout(checkServiceStatus, 10000);
}

// ============================================================================
// 辅助函数
// ============================================================================

function formatTime(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}分${secs}秒`;
}

// ============================================================================
// 查看日志
// ============================================================================

async function handleViewLogs() {
  try {
    // 获取日志数据
    const result = await chrome.storage.local.get('testLogs');
    const logs = result.testLogs || [];
    
    if (logs.length === 0) {
      alert('暂无测试日志');
      return;
    }
    
    // 创建日志窗口
    const logWindow = window.open('', '测试日志', 'width=800,height=600');
    
    if (!logWindow) {
      alert('无法打开日志窗口，请检查浏览器弹窗设置');
      return;
    }
    
    // 生成日志 HTML
    const logHtml = generateLogHtml(logs);
    logWindow.document.write(logHtml);
    logWindow.document.close();
    
    console.log('📄 打开日志窗口，共', logs.length, '条记录');
    
  } catch (error) {
    console.error('❌ 查看日志失败:', error);
    alert('查看日志失败: ' + error.message);
  }
}

function generateLogHtml(logs) {
  const logItems = logs.map((log, index) => {
    const date = new Date(log.timestamp).toLocaleString('zh-CN');
    const status = log.status === 'completed' ? '✅ 完成' : 
                   log.status === 'stopped' ? '⏹️ 停止' : 
                   log.status === 'error' ? '❌ 错误' : '⚠️ 未知';
    
    return `
      <div class="log-item">
        <div class="log-header">
          <span class="log-index">#${index + 1}</span>
          <span class="log-scenario">${log.scenarioName || '未知场景'}</span>
          <span class="log-status">${status}</span>
        </div>
        <div class="log-details">
          <div><strong>时间:</strong> ${date}</div>
          <div><strong>公司:</strong> ${log.companyName || 'N/A'}</div>
          <div><strong>轮次:</strong> ${log.rounds || 0}</div>
          <div><strong>耗时:</strong> ${formatTime(log.elapsed || 0)}</div>
          ${log.error ? `<div class="log-error"><strong>错误:</strong> ${log.error}</div>` : ''}
        </div>
      </div>
    `;
  }).join('');
  
  return `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>测试日志</title>
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          padding: 20px;
          background: #f5f5f5;
        }
        h1 {
          color: #1976d2;
          margin-bottom: 20px;
        }
        .log-item {
          background: white;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .log-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 12px;
          padding-bottom: 12px;
          border-bottom: 1px solid #e0e0e0;
        }
        .log-index {
          font-weight: bold;
          color: #666;
        }
        .log-scenario {
          flex: 1;
          font-weight: 500;
          color: #333;
        }
        .log-status {
          font-size: 14px;
        }
        .log-details {
          font-size: 13px;
          color: #666;
          line-height: 1.8;
        }
        .log-error {
          color: #f44336;
          margin-top: 8px;
        }
        .actions {
          margin-top: 20px;
          text-align: center;
        }
        button {
          padding: 10px 20px;
          background: #1976d2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          margin: 0 8px;
        }
        button:hover {
          background: #1565c0;
        }
      </style>
    </head>
    <body>
      <h1>📄 测试日志</h1>
      <div class="logs-container">
        ${logItems}
      </div>
      <div class="actions">
        <button onclick="window.print()">打印日志</button>
        <button onclick="exportLogs()">导出 JSON</button>
        <button onclick="clearLogs()">清空日志</button>
      </div>
      <script>
        function exportLogs() {
          const logs = ${JSON.stringify(logs)};
          const blob = new Blob([JSON.stringify(logs, null, 2)], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'test_logs_' + Date.now() + '.json';
          a.click();
          URL.revokeObjectURL(url);
        }
        
        function clearLogs() {
          if (confirm('确定要清空所有日志吗？')) {
            window.opener.postMessage({ action: 'CLEAR_LOGS' }, '*');
            window.close();
          }
        }
      </script>
    </body>
    </html>
  `;
}

// 监听来自日志窗口的消息
window.addEventListener('message', async (event) => {
  if (event.data.action === 'CLEAR_LOGS') {
    try {
      await chrome.storage.local.set({ testLogs: [] });
      console.log('🗑️ 日志已清空');
    } catch (error) {
      console.error('❌ 清空日志失败:', error);
    }
  }
});

// ============================================================================
// 打开设置
// ============================================================================

function handleOpenSettings() {
  // 打开设置页面
  chrome.windows.create({
    url: chrome.runtime.getURL('settings.html'),
    type: 'popup',
    width: 520,
    height: 650
  });
  
  console.log('⚙️ 打开设置页面');
}



// 监听设置更新
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === 'local' && changes.settings) {
    console.log('⚙️ 配置已更新');
    loadSettings();
    checkServiceStatus();
  }
});

console.log('✅ Popup UI 初始化完成');
