#!/usr/bin/env node
'use strict';

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

function redactSecrets(text) {
  if (typeof text !== 'string' || text.length === 0) return text;

  let out = text;

  // 常见 API Key 形态：sk-...
  out = out.replace(/\bsk-[A-Za-z0-9_-]{10,}\b/g, 'sk-*****');

  // 环境变量/日志里可能出现的 GROK_API_KEY=...
  out = out.replace(
    /(GROK_API_KEY\s*=\s*)(["']?)([^"'\r\n]+)\2/g,
    (_m, p1, p2) => `${p1}${p2}*****${p2}`,
  );

  // HTTP Header: Authorization: Bearer ...
  out = out.replace(/(Authorization:\s*Bearer\s+)([^\s\r\n]+)/gi, '$1*****');
  out = out.replace(/(Bearer\s+)(sk-[A-Za-z0-9_-]{10,})/gi, '$1sk-*****');

  return out;
}

function logErr(message) {
  process.stderr.write(`[grok-search-codex-proxy] ${redactSecrets(String(message))}\n`);
}

function detectClientMode(buf) {
  if (!buf || buf.length === 0) return null;

  // 跳过前导空白
  let i = 0;
  while (i < buf.length) {
    const c = buf[i];
    if (c === 0x20 || c === 0x09 || c === 0x0d || c === 0x0a) {
      i += 1;
      continue;
    }
    break;
  }
  if (i >= buf.length) return null;

  const first = buf[i];
  if (first === 0x7b /* { */ || first === 0x5b /* [ */) return 'ndjson';

  const prefix = buf.slice(i, Math.min(buf.length, i + 64)).toString('ascii');
  if (/^Content-Length:/i.test(prefix) || /^content-/i.test(prefix) || prefix.toLowerCase().includes('content-length')) {
    const hasHeaderEnd = buf.includes(Buffer.from('\r\n\r\n')) || buf.includes(Buffer.from('\n\n'));
    if (!hasHeaderEnd && buf.length < 128) return null;
    return 'content-length';
  }

  return 'ndjson';
}

function parseArgs(argv) {
  const result = { from: undefined, help: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') {
      result.help = true;
      continue;
    }
    if (arg === '--from' && i + 1 < argv.length) {
      result.from = argv[i + 1];
      i += 1;
      continue;
    }
    if (arg.startsWith('--from=')) {
      result.from = arg.slice('--from='.length);
      continue;
    }
  }
  return result;
}

function printHelp() {
  const text = [
    '用法：node stdio-proxy.js [--from <spec>]',
    '',
    '作用：将 Codex 的 MCP stdio(Content-Length 帧) ⇄ GrokSearch 的 NDJSON stdio 做双向桥接。',
    '',
    '--from：uvx 的来源 spec，可为本地路径或 git 仓库（例如：F:\\ai质控\\ai-blzk\\GrokSearch 或 git+https://...）。',
  ].join('\n');
  process.stderr.write(text + '\n');
}

const parsed = parseArgs(process.argv.slice(2));
if (parsed.help) {
  printHelp();
  process.exit(0);
}

const bundledFrom = path.resolve(__dirname, '..', 'assets', 'GrokSearch');
const defaultLocalFrom = 'F:\\ai质控\\ai-blzk\\GrokSearch';
const fromSpec =
  parsed.from ||
  process.env.GROK_SEARCH_FROM ||
  (fs.existsSync(bundledFrom)
    ? bundledFrom
    : fs.existsSync(defaultLocalFrom)
      ? defaultLocalFrom
      : 'git+https://github.com/GuDaStudio/GrokSearch');

const uvxArgs = fs.existsSync(fromSpec)
  ? ['--with-editable', fromSpec, 'grok-search']
  : ['--from', fromSpec, 'grok-search'];

const child = spawn('uvx', uvxArgs, {
  stdio: ['pipe', 'pipe', 'pipe'],
  env: process.env,
});

child.on('error', (err) => {
  logErr(`启动 uvx 失败：${err && err.message ? err.message : String(err)}`);
  process.exit(1);
});

child.stderr.setEncoding('utf8');
let childErrBuf = '';

function flushChildErrLines(force) {
  while (true) {
    const idx = childErrBuf.indexOf('\n');
    if (idx === -1) break;
    const line = childErrBuf.slice(0, idx + 1);
    childErrBuf = childErrBuf.slice(idx + 1);
    process.stderr.write(redactSecrets(line));
  }
  if (force && childErrBuf) {
    process.stderr.write(redactSecrets(childErrBuf));
    childErrBuf = '';
  }
}

child.stderr.on('data', (chunk) => {
  childErrBuf += chunk;
  flushChildErrLines(false);
});

child.stderr.on('end', () => {
  flushChildErrLines(true);
});

child.on('exit', (code, signal) => {
  if (signal) {
    logErr(`GrokSearch 进程退出（signal=${signal}）`);
    process.exit(1);
  }
  if (typeof code === 'number' && code !== 0) {
    logErr(`GrokSearch 进程退出（code=${code}）`);
    process.exit(code);
  }
  process.exit(0);
});

let clientMode = null; // 'content-length' | 'ndjson'
let pendingIn = Buffer.alloc(0);
let inputBuf = Buffer.alloc(0); // 仅用于 content-length 模式
let pendingChildStdout = '';

function pumpCodexFrames() {
  while (true) {
    const sep = inputBuf.indexOf('\r\n\r\n');
    if (sep === -1) return;

    const headerText = inputBuf.slice(0, sep).toString('ascii');
    const match = headerText.match(/Content-Length:\s*(\d+)/i);
    if (!match) {
      logErr(`无法解析 Content-Length 头：${JSON.stringify(headerText)}`);
      inputBuf = inputBuf.slice(sep + 4);
      continue;
    }

    const contentLength = Number.parseInt(match[1], 10);
    if (!Number.isFinite(contentLength) || contentLength < 0) {
      logErr(`非法 Content-Length：${match[1]}`);
      inputBuf = inputBuf.slice(sep + 4);
      continue;
    }

    const total = sep + 4 + contentLength;
    if (inputBuf.length < total) return;

    const bodyBuf = inputBuf.slice(sep + 4, total);
    inputBuf = inputBuf.slice(total);

    let msg;
    try {
      msg = JSON.parse(bodyBuf.toString('utf8'));
    } catch (e) {
      logErr(`解析 Codex JSON 失败：${e && e.message ? e.message : String(e)}`);
      continue;
    }

    const line = `${JSON.stringify(msg)}\n`;
    child.stdin.write(line, 'utf8');
  }
}

process.stdin.on('data', (chunk) => {
  if (clientMode === 'ndjson') {
    child.stdin.write(chunk);
    return;
  }

  if (clientMode === 'content-length') {
    inputBuf = Buffer.concat([inputBuf, chunk]);
    pumpCodexFrames();
    return;
  }

  pendingIn = Buffer.concat([pendingIn, chunk]);
  const mode = detectClientMode(pendingIn);
  if (!mode) return;
  clientMode = mode;
  logErr(`检测到客户端 framing：${clientMode}`);

  if (clientMode === 'ndjson') {
    child.stdin.write(pendingIn);
    pendingIn = Buffer.alloc(0);
    return;
  }

  inputBuf = pendingIn;
  pendingIn = Buffer.alloc(0);
  pumpCodexFrames();
});

process.stdin.on('end', () => {
  try {
    child.stdin.end();
  } catch {
    // ignore
  }
});

child.stdout.setEncoding('utf8');
let childOut = '';

function writeCodexFrame(obj) {
  const body = Buffer.from(JSON.stringify(obj), 'utf8');
  const header = Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, 'ascii');
  process.stdout.write(header);
  process.stdout.write(body);
}

function pumpChildLines() {
  while (true) {
    const idx = childOut.indexOf('\n');
    if (idx === -1) return;
    const rawLine = childOut.slice(0, idx);
    childOut = childOut.slice(idx + 1);

    const line = rawLine.trim();
    if (!line) continue;

    let msg;
    try {
      msg = JSON.parse(line);
    } catch (e) {
      logErr(`GrokSearch stdout 非 JSON：${line.slice(0, 200)}`);
      continue;
    }

    writeCodexFrame(msg);
  }
}

child.stdout.on('data', (chunk) => {
  if (!clientMode) {
    pendingChildStdout += chunk;
    return;
  }

  if (clientMode === 'ndjson') {
    if (pendingChildStdout) {
      process.stdout.write(pendingChildStdout);
      pendingChildStdout = '';
    }
    process.stdout.write(chunk);
    return;
  }

  // content-length
  if (pendingChildStdout) {
    childOut += pendingChildStdout;
    pendingChildStdout = '';
  }
  childOut += chunk;
  pumpChildLines();
});
