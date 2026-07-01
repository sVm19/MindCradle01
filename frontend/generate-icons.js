import sharp from 'sharp';
import fs from 'fs';
import path from 'path';

const svgPath = path.resolve('public/favicon.svg');
const dest192 = path.resolve('public/mindcradle-icon-192.png');
const dest512 = path.resolve('public/mindcradle-icon-512.png');

async function generateIcons() {
  try {
    if (!fs.existsSync(svgPath)) {
      console.error(`Error: favicon.svg not found at ${svgPath}`);
      process.exit(1);
    }

    console.log('Generating PWA PNG icons from SVG...');

    await sharp(svgPath)
      .resize(192, 192)
      .png()
      .toFile(dest192);
    console.log(`Generated: ${dest192}`);

    await sharp(svgPath)
      .resize(512, 512)
      .png()
      .toFile(dest512);
    console.log(`Generated: ${dest512}`);

    console.log('Icon generation completed successfully!');
  } catch (error) {
    console.error('Error generating icons:', error);
    process.exit(1);
  }
}

generateIcons();
