// ========================================
// 学生管理系统前端 - 静态文件复制脚本
// 用途：把 static/ 目录完整复制到 dist/
// EdgeOne / Vercel 等平台调用此脚本作为构建步骤
// ========================================

const fs = require('fs');
const path = require('path');

const SRC = 'static';
const DEST = 'dist';

// 递归复制目录
function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// 清空旧的 dist
if (fs.existsSync(DEST)) {
  fs.rmSync(DEST, { recursive: true, force: true });
  console.log(`[build] 清空旧目录: ${DEST}`);
}

// 复制
copyDir(SRC, DEST);
console.log(`[build] 复制完成: ${SRC}/ -> ${DEST}/`);

// 验证复制结果
const copied = fs.readdirSync(DEST);
console.log(`[build] dist 目录内容: ${copied.join(', ')}`);
console.log('[build] 构建完成 ✓');
