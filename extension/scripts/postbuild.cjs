const fs = require('fs');
const path = require('path');
const esbuild = require('esbuild');

const distDir = path.resolve(__dirname, '..', 'dist');
const publicDir = path.join(distDir, 'public');
const contentScriptEntry = path.resolve(__dirname, '..', 'content_scripts', 'content-script.tsx');
const contentScriptDest = path.join(distDir, 'content-script.js');
const backgroundEntry = path.resolve(__dirname, '..', 'background', 'index.ts');
const backgroundDest = path.join(distDir, 'background.js');

const ensureDir = (dirPath) => {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
};

const moveFile = (src, dest, transform) => {
  if (!fs.existsSync(src)) {
    console.warn(`Skipping move: ${path.relative(distDir, src)} not found.`);
    return;
  }

  ensureDir(path.dirname(dest));

  if (transform) {
    const contents = fs.readFileSync(src, 'utf-8');
    fs.writeFileSync(dest, transform(contents));
  } else {
    fs.copyFileSync(src, dest);
  }

  fs.unlinkSync(src);
  console.log(`Moved ${path.relative(distDir, src)} -> ${path.relative(distDir, dest)}`);
};

async function bundleContentScript() {
  await esbuild.build({
    entryPoints: [contentScriptEntry],
    bundle: true,
    outfile: contentScriptDest,
    format: 'iife',
    platform: 'browser',
    target: ['chrome120'],
    minify: true,
    jsx: 'automatic',
    define: {
      'process.env.NODE_ENV': '"production"',
    },
    treeShaking: true,
  });

  console.log('content-script.js bundled with esbuild');
}

async function bundleBackground() {
  await esbuild.build({
    entryPoints: [backgroundEntry],
    bundle: true,
    outfile: backgroundDest,
    format: 'iife',
    platform: 'browser',
    target: ['chrome120'],
    minify: true,
    define: {
      'process.env.NODE_ENV': '"production"',
    },
  });

  console.log('background.js bundled with esbuild');
}

async function run() {
  ensureDir(distDir);
  ensureDir(publicDir);

  moveFile(
    path.join(distDir, 'popup.html'),
    path.join(publicDir, 'popup.html'),
    (contents) => contents.replace('src="popup.js"', 'src="../popup.js"')
  );

  moveFile(
    path.join(distDir, 'icon128.png'),
    path.join(publicDir, 'icon128.png')
  );

  await bundleContentScript();
  await bundleBackground();

  const duplicatedManifest = path.join(distDir, 'manifest.json');
  if (fs.existsSync(duplicatedManifest)) {
    fs.unlinkSync(duplicatedManifest);
    console.log('Removed duplicated dist/manifest.json (manifest stays at project root)');
  }
}

run().catch((error) => {
  console.error('Post-build step failed:', error);
  process.exit(1);
});
