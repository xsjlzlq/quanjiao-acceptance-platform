const fs = require("fs");
let src = fs.readFileSync("G:/全椒县二轮延包/全椒县县级验收管理平台/backend/doc_exporter.py", "utf8");

// Township: replace the Find block for header replacement (lines ~384-391)
// Old: FindText with wrong number of spaces, ReplaceWith with format string
const OLD_TWN = `        # Replace headers in all 4 pages
        find = doc.Content.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        find.Execute(
            FindText="行政区划名称：                             ",
            ReplaceWith=f"行政区划名称：{township_name:<16} ",
            Replace=2
        )`;

// New: use wildcard to match 行政区划名称：+ any spaces, replace all 4 occurrences
// Template has exactly 29 spaces after the full-width colon
// We match the exact string and replace with name + padding to same total width (29 chars)
const NEW_TWN = `        # Replace 行政区划名称 in all 4 pages (template has 29 spaces after the colon)
        _fill = "全椒县" + township_name
        _pad = " " * max(0, 29 - len(_fill))
        _header_find    = "行政区划名称\\uff1a" + " " * 29
        _header_replace = "行政区划名称\\uff1a" + _fill + _pad
        find = doc.Content.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        find.Execute(FindText=_header_find, ReplaceWith=_header_replace, Replace=2)`;

// County: replace the Find block for county header replacement (lines ~428-435)
const OLD_CTY = `        find.Execute(
            FindText="行政区划名称：                             ",
            ReplaceWith="行政区划名称：全椒县                 ",
            Replace=2
        )`;

const NEW_CTY = `        _cty_find    = "行政区划名称\\uff1a" + " " * 29
        _cty_replace = "行政区划名称\\uff1a" + "全椒县" + " " * 26
        find.Execute(FindText=_cty_find, ReplaceWith=_cty_replace, Replace=2)`;

let changed = 0;
if (src.includes(OLD_TWN)) { src = src.replace(OLD_TWN, NEW_TWN); changed++; console.log("Township header block replaced"); }
else { console.log("Township block NOT FOUND"); }

if (src.includes(OLD_CTY)) { src = src.replace(OLD_CTY, NEW_CTY); changed++; console.log("County header block replaced"); }
else { console.log("County block NOT FOUND"); }

if (changed > 0) {
    fs.writeFileSync("G:/全椒县二轮延包/全椒县县级验收管理平台/backend/doc_exporter.py", src, "utf8");
    console.log("Saved OK");
}