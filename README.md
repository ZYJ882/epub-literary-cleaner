# EPUB Literary Cleaner

一个用于整理、修复、审查中文文学类 EPUB，并根据最终 EPUB 提取干净 UTF-8 TXT 的 Manus Skill。

## 功能

- 保留原版 EPUB 的封面、插图、CSS、字体、元数据和分级目录；
- 检查并清理乱码目录、错误重复、空白导航页和章节错位；
- 审查章节缺失、重复、顺序异常和前后文衔接问题；
- 区分作者有意的回忆、回环、照应与 EPUB 制作错误；
- 以 EPUB 的 NCX/nav 和 spine 为依据生成干净 TXT；
- 从 TXT 中排除封面、图片页、HTML/XML、CSS、网页按钮和评论区；
- 支持保留卷—章节树状目录，并保留末尾读者信等合法正文单元。

## 使用方式

将本目录作为 Manus Skill 安装后，直接提出类似请求：

- “整理并修复这个 EPUB，输出 EPUB 和 TXT”；
- “检查章节是否缺失、重复或前后文接不上”；
- “根据这个 EPUB 生成干净 TXT，保留分卷结构”。

也可以直接使用 TXT 提取脚本：

```bash
python3 scripts/epub_to_clean_txt.py input.epub output.txt
```

如果确实需要把封面、制作说明、内容介绍或角色图鉴等前置文字也写入 TXT：

```bash
python3 scripts/epub_to_clean_txt.py input.epub output.txt --include-frontmatter
```

## 安全原则

- 以用户原版 EPUB 为骨架进行修复，避免无必要地重建 manifest、spine、资源路径和目录；
- 不按乱码文件名推断章节顺序；
- 不仅凭算法就删除重复段落；
- 未经可靠来源核对，不用网络文本大规模替换用户正文；
- 正常图片保留在 EPUB 中，TXT 仅去除图片页和图片资源；
- 对缺章补回、重复删除、标题修正和目录改动建立说明。

## 目录结构

```text
SKILL.md                         # Manus Skill 主说明
scripts/audit_epub.py            # EPUB 结构与重复审查
scripts/epub_to_clean_txt.py     # 按 EPUB 目录提取干净 TXT
```

## 验证

```bash
python3 /home/ubuntu/skills/skill-creator/scripts/quick_validate.py .
python3 scripts/epub_to_clean_txt.py book.epub clean.txt
```

## 许可证

本项目采用 MIT License。该 Skill 不包含任何用户上传的书籍正文、图片或其他受版权保护的电子书内容。
