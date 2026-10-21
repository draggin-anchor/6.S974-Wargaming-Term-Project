// Write the deck's own theme colors into ppt/theme/theme1.xml after pptxgenjs has
// written the file (pptxgenjs always emits Office's stock palette).
const fs = require("fs");
const JSZip = require("jszip");
const SLOTS = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];

async function applyTheme(file, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const path = "ppt/theme/theme1.xml";
  let xml = await zip.file(path).async("string");
  for (const k of SLOTS) {
    const v = theme.colors[k];
    if (!/^[0-9A-Fa-f]{6}$/.test(v)) throw new Error(`theme color ${k} must be six hex digits`);
    const re = new RegExp(`<a:${k}>[\\s\\S]*?</a:${k}>`);
    if (!re.test(xml)) throw new Error(`slot ${k} not found in theme`);
    xml = xml.replace(re, `<a:${k}><a:srgbClr val="${v.toUpperCase()}"/></a:${k}>`);
  }
  xml = xml.replace(/<a:clrScheme name="[^"]*">/, `<a:clrScheme name="${theme.name}">`);
  zip.file(path, xml);
  fs.writeFileSync(file, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
}
module.exports = { applyTheme };
