#!/usr/bin/env node
'use strict';

/**
 * grok-search MCP 冒烟测试（Codex 侧 Content-Length framing）
 *
 * 目的：
 * - 快速验证 grok-search MCP（通过本技能的 stdio-proxy.js）是否能完成 initialize + tools/list
 * - 可选验证：get_config_info / web_search / web_fetch（会产生网络请求）
 *
 * 安全：
 * - 脚本会从 ~/.codex/config.toml 的 [mcp_servers.grok-search.env] 读取 GROK_API_URL/GROK_API_KEY
 * - 绝不打印 GROK_API_KEY 明文；输出会做二次脱敏（即使服务端已脱敏）
 */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

function parseArgs(argv) {
  const args = {
    help: false,
    configPath: undefined,
    serverName: 'grok-search',
    withConfigInfo: false,
    searchQuery: undefined,
    fetchUrl: undefined,
    platform: '',
    minResults: 3,
    maxResults: 10,
    timeoutMs: 60_000,
    verbose: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--help' || a === '-h') {
      args.help = true;
      continue;
    }
    if (a === '--config' && argv[i + 1]) {
      args.configPath = argv[i + 1];
      i += 1;
      continue;
    }
    if (a.startsWith('--config=')) {
      args.configPath = a.slice('--config='.length);
      continue;
    }
    if (a === '--server' && argv[i + 1]) {
      args.serverName = argv[i + 1];
      i += 1;
      continue;
    }
    if (a.startsWith('--server=')) {
      args.serverName = a.slice('--server='.length);
      continue;
    }
    if (a === '--with-config') {
      args.withConfigInfo = true;
      continue;
    }
    if (a === '--search' && argv[i + 1]) {
      args.searchQuery = argv[i + 1];
      i += 1;
      continue;
    }
    if (a.startsWith('--search=')) {
      args.searchQuery = a.slice('--search='.length);
      continue;
    }
    if (a === '--fetch' && argv[i + 1]) {
      args.fetchUrl = argv[i + 1];
      i += 1;
      continue;
    }
    if (a.startsWith('--fetch=')) {
      args.fetchUrl = a.slice('--fetch='.length);
      continue;
    }
    if (a === '--platform' && argv[i + 1]) {
      args.platform = argv[i + 1];
      i += 1;
      continue;
    }
    if (a.startsWith('--platform=')) {
      args.platform = a.slice('--platform='.length);
      continue;
    }
    if (a === '--min-results' && argv[i + 1]) {
      args.minResults = Number(argv[i + 1]);
      i += 1;
      continue;
    }
    if (a.startsWith('--min-results=')) {
      args.minResults = Number(a.slice('--min-results='.length));
      continue;
    }
    if (a === '--max-results' && argv[i + 1]) {
      args.maxResults = Number(argv[i + 1]);
      i += 1;
      continue;
    }
    if (a.startsWith('--max-results=')) {
      args.maxResults = Number(a.slice('--max-results='.length));
      continue;
    }
    if (a === '--timeout-ms' && argv[i + 1]) {
      args.timeoutMs = Number(argv[i + 1]);
      i += 1;
      continue;
    }
    if (a.startsWith('--timeout-ms=')) {
      args.timeoutMs = Number(a.slice('--timeout-ms='.length));
      continue;
    }
    if (a === '--verbose') {
      args.verbose = true;
      continue;
    }
  }

  return args;
}

function printHelp() {
  const text = [
    '用法：node scripts/mcp-smoke-test.js [options]',
    '',
    '选项：',
    '  --config <path>        指定 ~/.codex/config.toml 路径（默认自动推断）',
    '  --server <name>        MCP server 名（默认 grok-search）',
    '  --with-config          调用 get_config_info（会触发 /models 连接测试，产生网络请求）',
    '  --search <query>       调用 web_search（会产生网络请求）',
    '  --fetch <url>          调用 web_fetch（会产生网络请求）',
    '  --platform <p>         web_search 平台参数（默认空）',
    '  --min-results <n>      web_search min_results（默认 3）',
    '  --max-results <n>      web_search max_results（默认 10）',
    '  --timeout-ms <ms>      单个请求超时（默认 60000）',
    '  --verbose              输出更多 stderr（调试用）',
  ].join('\n');
  process.stderr.write(text + '\n');
}

function defaultCodexConfigPath() {
  const home = process.env.USERPROFILE || process.env.HOME;
  if (!home) return undefined;
  return path.join(home, '.codex', 'config.toml');
}

function loadEnvSectionFromToml(configText, sectionName) {
  const lines = configText.split(/\r?\n/);
  const header = `[${sectionName}]`;

  let inSection = false;
  const result = {};

  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;

    const isSectionHeader = line.startsWith('[') && line.endsWith(']');
    if (isSectionHeader) {
      inSection = line === header;
      continue;
    }
    if (!inSection) continue;

    const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)\s*$/);
    if (!m) continue;
    const key = m[1];
    let value = m[2];

    // 仅解析字符串：KEY="..." 或 KEY='...'
    if (value.startsWith('"')) {
      const sm = value.match(/^"((?:\\.|[^"\\])*)"/);
      if (!sm) continue;
      value = sm[1]
        .replace(/\\n/g, '\n')
        .replace(/\\r/g, '\r')
        .replace(/\\t/g, '\t')
        .replace(/\\"/g, '"')
        .replace(/\\\\/g, '\\');
    } else if (value.startsWith("'")) {
      const sm = value.match(/^'([^']*)'/);
      if (!sm) continue;
      value = sm[1];
    } else {
      continue;
    }

    result[key] = value;
  }

  return result;
}

function loadGrokEnvFromCodexConfig(configPath, serverName) {
  if (!configPath || !fs.existsSync(configPath)) return {};
  const text = fs.readFileSync(configPath, 'utf8');
  return loadEnvSectionFromToml(text, `mcp_servers.${serverName}.env`);
}

function redactSensitiveText(text) {
  if (typeof text !== 'string') return text;
  // 常见 key 形态：sk-...
  return text.replace(/\bsk-[A-Za-z0-9_-]{10,}\b/g, 'sk-*****');
}

function redactObject(value) {
  if (value === null || value === undefined) return value;
  if (Array.isArray(value)) return value.map(redactObject);
  if (typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) {
      const upper = k.toUpperCase();
      if (upper.includes('API_KEY') || upper.includes('GROK_API_KEY') || upper === 'AUTHORIZATION') {
        out[k] = '*****';
        continue;
      }
      out[k] = redactObject(v);
    }
    return out;
  }
  if (typeof value === 'string') return redactSensitiveText(value);
  return value;
}

function withTimeout(promise, timeoutMs, label) {
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => {
      reject(new Error(`${label} 超时（${timeoutMs}ms）`));
    }, timeoutMs);
    promise
      .then((v) => {
        clearTimeout(t);
        resolve(v);
      })
      .catch((e) => {
        clearTimeout(t);
        reject(e);
      });
  });
}

class McpStdioClient {
  constructor(child, opts) {
    this.child = child;
    this.verbose = Boolean(opts && opts.verbose);
    this.timeoutMs = Number(opts && opts.timeoutMs) || 60_000;
    this.nextId = 1;
    this.pending = new Map();
    this.stdoutBuf = Buffer.alloc(0);
    this.closed = false;

    child.stdout.on('data', (chunk) => this.#onStdout(chunk));
    child.stderr.on('data', (chunk) => this.#onStderr(chunk));
    child.on('exit', (code, signal) => this.#onExit(code, signal));
    child.on('error', (err) => this.#onError(err));
  }

  #onStdout(chunk) {
    this.stdoutBuf = Buffer.concat([this.stdoutBuf, chunk]);
    this.#pumpFrames();
  }

  #pumpFrames() {
    while (true) {
      const sep = this.stdoutBuf.indexOf('\r\n\r\n');
      if (sep === -1) return;

      const headerText = this.stdoutBuf.slice(0, sep).toString('ascii');
      const match = headerText.match(/Content-Length:\s*(\d+)/i);
      if (!match) {
        // 不是合法帧，丢弃头部，避免死循环
        this.stdoutBuf = this.stdoutBuf.slice(sep + 4);
        continue;
      }
      const contentLength = Number.parseInt(match[1], 10);
      const total = sep + 4 + contentLength;
      if (this.stdoutBuf.length < total) return;

      const body = this.stdoutBuf.slice(sep + 4, total).toString('utf8');
      this.stdoutBuf = this.stdoutBuf.slice(total);

      let msg;
      try {
        msg = JSON.parse(body);
      } catch {
        continue;
      }

      this.#dispatch(msg);
    }
  }

  #dispatch(msg) {
    if (!msg || typeof msg !== 'object') return;
    if (Object.prototype.hasOwnProperty.call(msg, 'id') && this.pending.has(msg.id)) {
      const pending = this.pending.get(msg.id);
      this.pending.delete(msg.id);
      if (msg.error) pending.reject(new Error(JSON.stringify(redactObject(msg.error))));
      else pending.resolve(msg);
    }
  }

  #onStderr(chunk) {
    if (!this.verbose) return;
    process.stderr.write(chunk);
  }

  #onExit(code, signal) {
    this.closed = true;
    const err = new Error(`MCP 子进程退出：code=${code}, signal=${signal || '-'}`);
    for (const p of this.pending.values()) p.reject(err);
    this.pending.clear();
  }

  #onError(err) {
    this.closed = true;
    const e = err instanceof Error ? err : new Error(String(err));
    for (const p of this.pending.values()) p.reject(e);
    this.pending.clear();
  }

  sendNotification(method, params) {
    const msg = params === undefined ? { jsonrpc: '2.0', method } : { jsonrpc: '2.0', method, params };
    this.#write(msg);
  }

  async request(method, params) {
    const id = this.nextId++;
    const msg = params === undefined ? { jsonrpc: '2.0', id, method } : { jsonrpc: '2.0', id, method, params };

    const p = new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
    });

    this.#write(msg);
    const resp = await withTimeout(p, this.timeoutMs, `${method}(${id})`);
    return resp;
  }

  #write(obj) {
    if (this.closed) throw new Error('MCP 子进程已退出，无法发送请求');
    const json = JSON.stringify(obj);
    const body = Buffer.from(json, 'utf8');
    const header = Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, 'ascii');
    this.child.stdin.write(header);
    this.child.stdin.write(body);
  }

  close() {
    try {
      this.child.kill();
    } catch {
      // ignore
    }
  }
}

function extractToolTextContent(toolCallResult) {
  const result = toolCallResult && toolCallResult.result;
  if (!result) return undefined;

  // fastmcp 常见返回结构：{ content: [{ type: 'text', text: '...' }] }
  const content = result.content;
  if (Array.isArray(content)) {
    const firstText = content.find((c) => c && c.type === 'text' && typeof c.text === 'string');
    if (firstText) return firstText.text;
  }

  // 兼容：直接返回 string
  if (typeof result === 'string') return result;

  return undefined;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    process.exit(0);
  }

  const skillRoot = path.resolve(__dirname, '..');
  const proxyScript = path.join(__dirname, 'stdio-proxy.js');
  const fromDir = path.join(skillRoot, 'assets', 'GrokSearch');
  const configPath = args.configPath || defaultCodexConfigPath();
  const envFromConfig = loadGrokEnvFromCodexConfig(configPath, args.serverName);

  const childEnv = { ...process.env, ...envFromConfig };
  const child = spawn(process.execPath, [proxyScript, '--from', fromDir], {
    stdio: ['pipe', 'pipe', 'pipe'],
    env: childEnv,
  });

  const client = new McpStdioClient(child, { timeoutMs: args.timeoutMs, verbose: args.verbose });

  try {
    const initResp = await client.request('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'grok-search-codex-proxy-smoke', version: '0.1.0' },
    });

    const initResult = initResp.result || {};
    const serverInfo = initResult.serverInfo || {};
    process.stdout.write(
      `[OK] initialize: server=${serverInfo.name || '-'} version=${serverInfo.version || '-'}\n`
    );

    client.sendNotification('notifications/initialized', {});

    const toolsResp = await client.request('tools/list', {});
    const tools = (toolsResp.result && toolsResp.result.tools) || [];
    const names = tools.map((t) => t && t.name).filter(Boolean);
    process.stdout.write(`[OK] tools/list: ${names.join(', ') || '(empty)'}\n`);

    const required = ['web_search', 'web_fetch', 'get_config_info'];
    const missing = required.filter((n) => !names.includes(n));
    if (missing.length > 0) {
      process.stdout.write(`[WARN] 缺少工具：${missing.join(', ')}\n`);
    }

    if (args.withConfigInfo) {
      const cfgResp = await client.request('tools/call', { name: 'get_config_info', arguments: {} });
      const cfgText = extractToolTextContent(cfgResp);
      if (cfgText) {
        const secretLike = /\bsk-[A-Za-z0-9_-]{10,}\b/.test(cfgText);
        let cfgObj;
        try {
          cfgObj = JSON.parse(cfgText);
        } catch {
          cfgObj = undefined;
        }
        if (cfgObj && typeof cfgObj === 'object') {
          const rawKey = cfgObj.GROK_API_KEY;
          if (typeof rawKey === 'string' && rawKey !== '***' && rawKey !== '未配置') {
            process.stdout.write('[WARN] get_config_info 返回的 GROK_API_KEY 不是 "***"（已在输出层剔除）。建议检查服务端脱敏逻辑。\n');
          } else if (secretLike) {
            process.stdout.write('[WARN] get_config_info 原始返回疑似包含 sk- 形态密钥（已在输出层剔除）。建议检查服务端脱敏逻辑。\n');
          }
          // 二次脱敏：不输出 key（即使已脱敏）
          delete cfgObj.GROK_API_KEY;
          if (
            !args.verbose &&
            cfgObj.connection_test &&
            typeof cfgObj.connection_test === 'object' &&
            Array.isArray(cfgObj.connection_test.available_models)
          ) {
            cfgObj.connection_test.available_models_count = cfgObj.connection_test.available_models.length;
            delete cfgObj.connection_test.available_models;
          }
          process.stdout.write(`[OK] get_config_info:\n${JSON.stringify(redactObject(cfgObj), null, 2)}\n`);
        } else {
          process.stdout.write(`[OK] get_config_info(raw):\n${redactSensitiveText(cfgText)}\n`);
        }
      } else {
        process.stdout.write('[WARN] get_config_info 无文本返回\n');
      }
    } else {
      process.stdout.write('[SKIP] get_config_info（使用 --with-config 启用）\n');
    }

    if (args.searchQuery) {
      const resp = await client.request('tools/call', {
        name: 'web_search',
        arguments: {
          query: args.searchQuery,
          platform: args.platform,
          min_results: args.minResults,
          max_results: args.maxResults,
        },
      });
      const text = extractToolTextContent(resp);
      process.stdout.write('[OK] web_search:\n');
      process.stdout.write(text ? `${redactSensitiveText(text)}\n` : '(empty)\n');
    }

    if (args.fetchUrl) {
      const resp = await client.request('tools/call', { name: 'web_fetch', arguments: { url: args.fetchUrl } });
      const text = extractToolTextContent(resp);
      const head = typeof text === 'string' ? text.slice(0, 800) : '';
      process.stdout.write('[OK] web_fetch(head 800 chars):\n');
      process.stdout.write(head ? `${redactSensitiveText(head)}\n` : '(empty)\n');
    }
  } finally {
    client.close();
  }
}

main().catch((err) => {
  const msg = err && err.message ? err.message : String(err);
  process.stderr.write(`[FAIL] ${redactSensitiveText(msg)}\n`);
  process.exit(1);
});
